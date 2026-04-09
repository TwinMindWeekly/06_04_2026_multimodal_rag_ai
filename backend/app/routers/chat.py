"""POST /api/chat — SSE streaming chat endpoint (CHAT-01, CHAT-04, CHAT-05, CHAT-06).

Pipeline: validate request -> embed query -> MMR search -> build context ->
ChatPromptTemplate -> LLM.astream() -> SSE events -> terminal citation event.
"""
import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.domain import ChatRequest
from app.services.embeddings import EmbeddingFactory
from app.services.llm_provider import LLMProviderFactory
from app.services.rag_chain import build_context_with_citations, chat_prompt
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(tags=['chat'])


async def _generate_sse_events(request: ChatRequest) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE-formatted events.

    CHAT-05 format:
      data: {"text": "..."}\\n\\n          — for each LLM chunk
      data: {"done": true, "citations": [...]}\\n\\n  — terminal event
    CHAT-06 format:
      data: {"error": "..."}\\n\\n        — on any error mid-stream
    """
    try:
        # 1. Get embedding model (CHAT-02 step 1)
        embedding_model = EmbeddingFactory.get_embedding_model(
            provider=request.embedding_provider,
            api_key=request.embedding_api_key,
        )

        # 2. MMR search — synchronous ChromaDB call, wrap in to_thread (Pitfall 2, T-4a-06)
        chunks = await asyncio.to_thread(
            vector_store.similarity_search_mmr,
            query=request.message,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            project_id=request.project_id,
            embedding_model=embedding_model,
            provider=request.embedding_provider,
        )

        # 3. Build context with citation markers (CHAT-02, CHAT-07)
        context_str, citations = build_context_with_citations(chunks)

        # 4. Format prompt (CHAT-03)
        messages = chat_prompt.format_messages(
            context=context_str or 'No relevant documents found.',
            question=request.message,
        )

        # 5. Get LLM with streaming (CHAT-04)
        llm = LLMProviderFactory.get_llm(
            provider=request.provider,
            api_key=request.api_key,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            streaming=True,
        )

        # 6. Stream LLM response as SSE text events (CHAT-05)
        async for chunk in llm.astream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                yield f'data: {json.dumps({"text": chunk.content})}\n\n'

        # 7. Terminal event with citations (CHAT-05, CHAT-07)
        yield f'data: {json.dumps({"done": True, "citations": citations})}\n\n'

    except Exception as e:
        # CHAT-06: Error event mid-stream — do NOT raise HTTPException (T-4a-04)
        logger.exception('Chat stream error: %s', e)
        yield f'data: {json.dumps({"error": str(e)})}\n\n'


@router.post('/api/chat')
async def chat(request: ChatRequest) -> StreamingResponse:
    """POST /api/chat — RAG-augmented chat with SSE streaming (CHAT-01, CHAT-04)."""
    return StreamingResponse(
        _generate_sse_events(request),
        media_type='text/event-stream',
        headers={
            'X-Accel-Buffering': 'no',
            'Cache-Control': 'no-cache',
        },
    )
