"""RAG chain service: context building and prompt template (CHAT-02, CHAT-03, CHAT-07).

Pipeline: embed query -> MMR search -> build_context_with_citations -> ChatPromptTemplate -> LLM.astream()
This module handles steps 3 (context building) and 4 (prompt template).
Steps 1-2 and 5 are handled in the chat router.
"""
from langchain_core.prompts import ChatPromptTemplate


RAG_SYSTEM_PROMPT = (
    'You are a helpful assistant. Answer the question based ONLY on the provided context. '
    'If the context does not contain enough information, say so clearly. '
    'Use citation markers [1], [2], etc. when referencing specific parts of the context.\n\n'
    'Context:\n{context}'
)

chat_prompt = ChatPromptTemplate.from_messages([
    ('system', RAG_SYSTEM_PROMPT),
    ('human', '{question}'),
])


def build_context_with_citations(
    chunks: list[dict],
) -> tuple[str, list[dict]]:
    """Build context string from MMR search results with citation markers.

    Args:
        chunks: Output from vector_store.similarity_search_mmr().
                Each dict has keys: content, metadata, similarity, distance.

    Returns:
        (context_string, citations_list) where citations_list contains dicts
        with filename, page_number, chunk_index, marker for each chunk.
    """
    if not chunks:
        return '', []

    context_parts: list[str] = []
    citations: list[dict] = []

    for i, chunk in enumerate(chunks):
        marker = f'[{i + 1}]'
        meta = chunk.get('metadata', {})
        context_parts.append(f'{marker} {chunk["content"]}')
        citations.append({
            'filename': meta.get('filename', ''),
            'page_number': meta.get('page_number', 0),
            'chunk_index': meta.get('chunk_index', 0),
            'marker': marker,
        })

    return '\n\n'.join(context_parts), citations
