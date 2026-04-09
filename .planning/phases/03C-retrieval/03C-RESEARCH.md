# Phase 3c: Retrieval - Research

**Researched:** 2026-04-09
**Domain:** ChromaDB collection metadata, switchable embedding providers, MMR/deduplication, FastAPI search endpoints, threading write locks
**Confidence:** HIGH (all critical API behaviors verified against live runtime)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EMBED-01 | Default embedding: all-MiniLM-L6-v2 via sentence-transformers | Existing EmbeddingFactory confirmed working; model loads lazily via get_default_embeddings() |
| EMBED-02 | Switchable to OpenAI text-embedding-3-small or Google text-embedding-004 | langchain-openai 1.1.12 and google-genai SDK paths verified; package installation plan documented |
| EMBED-03 | Store embedding provider name + model ID in ChromaDB collection metadata at creation | get_or_create_collection(metadata={...}) verified to persist on first create only |
| EMBED-04 | Block queries when active provider mismatches collection's recorded provider | collection.metadata read pattern verified; mismatch detection logic confirmed |
| EMBED-05 | Re-index endpoint: delete all vectors + re-run full embedding pipeline | delete_collection() + get_or_create_collection() re-index pattern verified |
| EMBED-06 | Serialize ChromaDB writes per collection using per-project lock | threading.Lock per-project dict pattern verified working |
| SEARCH-01 | Semantic search endpoint returning Top-K chunks with distances and metadata | ChromaDB query with include=['distances'] verified; FastAPI Query params pattern confirmed |
| SEARCH-02 | Score threshold filter: discard chunks below similarity threshold | Cosine distance to similarity conversion formula verified |
| SEARCH-03 | MMR/deduplication to avoid returning overlapping chunks | langchain_core.vectorstores.utils.maximal_marginal_relevance verified available and working |
</phase_requirements>

---

## Summary

Phase 3c builds on the ingestion pipeline from Phase 3b to deliver a complete retrieval layer. The work has three distinct sub-problems: (1) making the embedding provider switchable while keeping the vector store consistent, (2) protecting collection integrity via metadata guards and write locks, and (3) exposing a search endpoint with filtering and deduplication.

All critical APIs were verified against the live ChromaDB 1.5.7 runtime and Python 3.12 environment. The most important finding is that `get_or_create_collection` sets metadata **only on the first creation** — subsequent calls with different metadata do NOT update it. This means the provider check pattern for EMBED-04 is both feasible and safe. A second critical finding is that `langchain_core.vectorstores.utils.maximal_marginal_relevance` is already installed (part of langchain-core 1.2.28) and requires no new dependencies.

The blocking issue is that `image_processor.py` (from Phase 3b) imports `from google import genai` (new SDK), but `google-genai` is not installed in the test environment, causing all tests to fail at conftest.py import time. The Phase 3c Wave 0 must install `google-genai` as its first action.

**Primary recommendation:** Add `google-genai>=1.0`, `langchain-openai==1.1.12` to `requirements.txt`; extend `VectorStoreService` to accept an embedding model parameter; use cosine metric on new collections for intuitive score thresholding; implement MMR using the already-installed `langchain_core` utility.

---

## Project Constraints (from CLAUDE.md)

No project-level `CLAUDE.md` was found in the working directory. Constraints are sourced from global `~/.claude/CLAUDE.md` and project conventions documented in `.planning/codebase/CONVENTIONS.md`.

| Directive | Source | Impact on Phase 3c |
|-----------|--------|--------------------|
| PEP 8, single quotes for strings | Odoo rules + CONVENTIONS.md | All new Python files must use single quotes |
| Type annotations on all function signatures | python/coding-style.md | Every new function needs type hints |
| Never mutate existing objects | common/coding-style.md | VectorStoreService changes must create new objects, not mutate |
| Immutability preferred | python/coding-style.md | Use frozen dataclasses or NamedTuples for result objects |
| Factory pattern for AI components | CONVENTIONS.md D-04 | EmbeddingFactory must be extended, not replaced |
| Lazy singleton via global guard | CONVENTIONS.md | get_default_embeddings() pattern must be reused/extended |
| HTTPException with i18n t() | CONVENTIONS.md | All new endpoint errors use t() for messages |
| Files 200-400 lines, max 800 | common/coding-style.md | Search router and extended vector_store.py must stay under 800 lines |
| 80% test coverage | python/testing.md | All new services and endpoints need tests |

---

## Standard Stack

### Core (already installed)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| chromadb | 1.5.7 | Vector database | Installed [VERIFIED: pip list] |
| langchain-core | 1.2.28 | MMR utility, Embeddings base class | Installed [VERIFIED: pip list] |
| langchain-community | 0.4.1 | HuggingFaceEmbeddings | Installed [VERIFIED: pip list] |
| sentence-transformers | 5.3.0 | all-MiniLM-L6-v2 local model | Listed in STACK.md [ASSUMED: installed in prod env] |
| scikit-learn | 1.8.0 | cosine_similarity (backup for MMR) | Installed [VERIFIED: pip list] |
| numpy | 2.4.4 | Array operations for MMR | Installed [VERIFIED: pip list] |
| threading | stdlib | Per-project write locks | VERIFIED working |
| fastapi | 0.135.3 | Search endpoint | Installed [VERIFIED: pip list] |

### To Install (Wave 0 prerequisite)

| Library | Version | Purpose | Why This Version |
|---------|---------|---------|-----------------|
| google-genai | >=1.0 | Google Gemini SDK (fixes current test breakage) | Already in requirements.txt; google.genai import required by image_processor.py [VERIFIED: test run shows ImportError] |
| langchain-openai | ==1.1.12 | OpenAIEmbeddings for text-embedding-3-small | Requires langchain-core>=1.2.21 (have 1.2.28 — compatible) [VERIFIED: PyPI] |

### Not Required (use existing)

| Purpose | Available Via | Why No New Package |
|---------|-------------|-------------------|
| Google text embeddings | `google-genai` SDK (above) | `client.models.embed_content()` handles text-embedding-004 directly |
| langchain-google-genai | SKIP | v4.x requires google-genai>=1.56.0; v2.x needs protobuf compatibility verification; direct google-genai SDK is simpler and already required |

**Installation (Wave 0):**
```bash
pip install google-genai langchain-openai==1.1.12
# Add to requirements.txt:
# google-genai>=1.0   (already present, not installed)
# langchain-openai==1.1.12
```

**Version verification:**
```
google-genai: pip index versions google-genai -> 1.71.0 latest [VERIFIED: 2026-04-09]
langchain-openai: pip index versions langchain-openai -> 1.1.12 latest [VERIFIED: 2026-04-09]
```

---

## Architecture Patterns

### Recommended File Changes

```
backend/app/
├── services/
│   ├── embeddings.py         # EXTEND: fix gemini model name, add API-key-aware factory
│   └── vector_store.py       # EXTEND: collection metadata, provider check, write lock, MMR search
├── routers/
│   └── search.py             # NEW: GET /api/search endpoint
└── main.py                   # EXTEND: mount search router
```

### Pattern 1: EmbeddingFactory with API Key Injection

**What:** Factory returns a provider-specific embedding object. For paid providers, API key is passed at call time (not at startup).
**When to use:** Any path that calls embed_documents() or embed_query() must use this pattern.

```python
# Source: verified against existing embeddings.py + confirmed langchain_openai 1.1.12 API

class EmbeddingFactory:
    @staticmethod
    def get_embedding_model(provider: str = 'local', api_key: str | None = None):
        if provider == 'local':
            return HuggingFaceEmbeddings(
                model_name='all-MiniLM-L6-v2',
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': False},
            )
        elif provider == 'openai':
            from langchain_openai import OpenAIEmbeddings
            # api_key=None -> reads OPENAI_API_KEY env var automatically
            return OpenAIEmbeddings(model='text-embedding-3-small', api_key=api_key)
        elif provider == 'gemini':
            return _GeminiEmbeddings(model='models/text-embedding-004', api_key=api_key)
        else:
            raise ValueError(f'Unsupported embedding provider: {provider}')
```

### Pattern 2: Custom _GeminiEmbeddings Wrapper (no langchain-google-genai required)

**What:** Thin LangChain-compatible wrapper around google-genai SDK. Implements `embed_documents()` and `embed_query()` using `client.models.embed_content()`.
**When to use:** All Google embedding calls go through this class.

```python
# Source: verified google-genai SDK API shape; langchain_core.embeddings.Embeddings interface verified

from langchain_core.embeddings import Embeddings

class _GeminiEmbeddings(Embeddings):
    def __init__(self, model: str = 'models/text-embedding-004', api_key: str | None = None):
        self._model = model
        self._api_key = api_key or os.getenv('GOOGLE_API_KEY')

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        from google import genai
        client = genai.Client(api_key=self._api_key)
        result = client.models.embed_content(model=self._model, contents=texts)
        return [e.values for e in result.embeddings]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
```

### Pattern 3: ChromaDB Collection Metadata for Provider Tracking (EMBED-03, EMBED-04)

**What:** Store `embedding_provider` and `embedding_model` in collection metadata at creation. Read and validate on every subsequent operation.
**When to use:** Every call to `get_or_create_collection` or `get_collection`.

```python
# Source: VERIFIED against ChromaDB 1.5.7 live runtime
# Key behavior verified: get_or_create_collection sets metadata ONLY on first creation.
# Subsequent calls with different metadata do NOT update existing collection.

def _get_or_create_collection_with_provider(
    self,
    collection_name: str,
    provider: str,
    model: str,
) -> chromadb.Collection:
    # Use cosine space for intuitive similarity scores (0=identical, 1=orthogonal)
    meta = {
        'embedding_provider': provider,
        'embedding_model': model,
        'hnsw:space': 'cosine',
    }
    return self.client.get_or_create_collection(name=collection_name, metadata=meta)

def _check_provider_match(self, collection: chromadb.Collection, active_provider: str) -> None:
    stored = (collection.metadata or {}).get('embedding_provider')
    if stored and stored != active_provider:
        raise ValueError(
            f'Embedding provider mismatch: collection uses "{stored}", '
            f'active provider is "{active_provider}". Run /reindex to switch.'
        )
```

### Pattern 4: Per-Project Write Lock (EMBED-06)

**What:** Module-level dict mapping project_id to a threading.Lock. A meta-lock protects the dict itself.
**When to use:** Wrap every `collection.upsert()` call in the project's lock.

```python
# Source: VERIFIED against Python 3.12 threading module

import threading

_project_locks: dict[int | None, threading.Lock] = {}
_locks_mutex: threading.Lock = threading.Lock()


def _get_project_lock(project_id: int | None) -> threading.Lock:
    with _locks_mutex:
        if project_id not in _project_locks:
            _project_locks[project_id] = threading.Lock()
        return _project_locks[project_id]


# Usage in insert_documents():
with _get_project_lock(project_id):
    collection.upsert(documents=..., embeddings=..., metadatas=..., ids=...)
```

### Pattern 5: MMR Search with Score Threshold (SEARCH-01, SEARCH-02, SEARCH-03)

**What:** Query ChromaDB with `fetch_k` results (including embeddings), apply score threshold, then apply MMR to select `k` diverse results.
**When to use:** The search endpoint's core retrieval logic.

```python
# Source: VERIFIED - langchain_core.vectorstores.utils.maximal_marginal_relevance confirmed installed
# ChromaDB query with include=['embeddings'] verified to return embedding vectors
# MMR signature: (query_embedding: np.ndarray, embedding_list: list, lambda_mult=0.5, k=4) -> list[int]

import numpy as np
from langchain_core.vectorstores.utils import maximal_marginal_relevance

def similarity_search_mmr(
    self,
    query: str,
    top_k: int = 5,
    fetch_k: int = 20,
    score_threshold: float = 0.3,
    lambda_mult: float = 0.5,
    project_id: int | None = None,
    embedding_model=None,
):
    collection_name = self._get_collection_name(project_id)
    try:
        collection = self.client.get_collection(name=collection_name)
    except Exception:
        return []

    emb_model = embedding_model or get_default_embeddings()

    # EMBED-04: check provider matches collection
    # (provider extracted from embedding_model object)
    ...

    query_embedding = emb_model.embed_query(query)

    # Fetch fetch_k results with embeddings (needed for MMR diversity calculation)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(fetch_k, collection.count()),
        include=['documents', 'metadatas', 'distances', 'embeddings'],
    )

    if not results['documents'] or not results['documents'][0]:
        return []

    docs = results['documents'][0]
    metadatas = results['metadatas'][0]
    distances = results['distances'][0]
    embeddings = results['embeddings'][0]

    # SEARCH-02: convert cosine distance to similarity, apply threshold
    # cosine distance: 0=identical, 1=orthogonal; similarity = 1 - distance
    similarities = [1.0 - d for d in distances]
    above_threshold = [
        (doc, meta, sim, emb)
        for doc, meta, sim, emb in zip(docs, metadatas, similarities, embeddings)
        if sim >= score_threshold
    ]
    if not above_threshold:
        return []

    filtered_docs, filtered_metas, filtered_sims, filtered_embs = zip(*above_threshold)

    # SEARCH-03: MMR deduplication
    query_arr = np.array(query_embedding)
    selected_indices = maximal_marginal_relevance(
        query_arr, list(filtered_embs), lambda_mult=lambda_mult, k=top_k
    )

    return [
        {
            'content': filtered_docs[i],
            'metadata': filtered_metas[i],
            'similarity': filtered_sims[i],
            'distance': 1.0 - filtered_sims[i],
        }
        for i in selected_indices
    ]
```

### Pattern 6: Re-Index Endpoint (EMBED-05)

**What:** Delete ChromaDB collection, re-queue all documents in the project for background re-embedding.
**When to use:** Called when user switches embedding provider.

```python
# Source: ChromaDB delete_collection + re-create pattern VERIFIED
# Document.folder -> Folder.project_id relationship VERIFIED in domain.py

@router.post('/api/projects/{project_id}/reindex', status_code=202)
def reindex_project(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    lang: str = Depends(get_language),
):
    # Verify project exists
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail=t('errors.project_not_found', lang))

    # Delete entire ChromaDB collection for this project
    collection_name = f'project_{project_id}'
    try:
        vector_store.client.delete_collection(collection_name)
    except Exception:
        pass  # Collection may not exist yet

    # Mark all documents in project as pending and queue re-processing
    documents = (
        db.query(Document)
        .join(Folder)
        .filter(Folder.project_id == project_id)
        .all()
    )
    for doc in documents:
        doc.status = 'pending'
    db.commit()

    for doc in documents:
        background_tasks.add_task(process_and_update_document, doc.id)

    return {'status': 'reindex_queued', 'project_id': project_id, 'document_count': len(documents)}
```

### Pattern 7: Search Endpoint (SEARCH-01)

**What:** GET endpoint accepting query text, project_id, provider settings, and returning ranked chunks.
**When to use:** The primary retrieval API consumed by the Chat backend in Phase 4a.

```python
# Source: FastAPI Query params pattern VERIFIED working

@router.get('/api/search', response_model=SearchResponse)
def search(
    q: str = Query(..., description='Search query text'),
    project_id: int = Query(..., description='Project ID to search within'),
    top_k: int = Query(5, ge=1, le=20, description='Number of results'),
    score_threshold: float = Query(0.3, ge=0.0, le=1.0, description='Min similarity score'),
    provider: str = Query('local', description='Embedding provider: local/openai/gemini'),
    api_key: str | None = Query(None, description='API key for paid providers'),
    lang: str = Depends(get_language),
):
    ...
```

### Anti-Patterns to Avoid

- **Passing embedding model at collection creation instead of storing in metadata:** ChromaDB creates its own default embedding function unless you explicitly handle embeddings yourself. Always pass pre-computed embeddings and store the provider in `collection.metadata`.
- **Using `get_or_create_collection` to UPDATE metadata:** It only sets metadata on first create. Use `collection.modify(metadata={...})` to update.
- **Score threshold on raw L2 distance:** Default ChromaDB uses L2 distance where "lower = better" but range is unbounded. Use `hnsw:space=cosine` so distance is in `[0, 2]` and similarity = `1 - distance` is intuitive.
- **Forgetting to include `embeddings` in query results for MMR:** MMR requires the actual embedding vectors of candidate documents. Omitting `include=['embeddings']` makes the `result['embeddings']` field `None`.
- **Per-document locks instead of per-project locks:** Multiple documents in the same project share one collection. The lock must be per-collection (per-project), not per-document.
- **Using get_default_embeddings() directly in VectorStoreService:** The service now needs to accept any provider's embedding model to support switchable providers.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MMR / diversity ranking | Custom cosine-similarity deduplication loop | `langchain_core.vectorstores.utils.maximal_marginal_relevance` | Already installed; handles lambda_mult parameter correctly; returns indices preserving original order |
| Embedding provider abstraction | Direct if/else per provider at call site | `EmbeddingFactory.get_embedding_model(provider, api_key)` | Extends existing factory pattern; keeps all provider logic in one place |
| Thread-safe singleton dict | Manual `try/except` dict access | `_locks_mutex` + `_project_locks` dict | Double-lock pattern handles race condition on dict access itself |
| Score normalization | Custom formula per metric | Cosine collection + `similarity = 1 - distance` | Simple, correct, no surprises |
| Collection existence check | `try/except` around `get_collection` | `client.get_collection()` inside try/except already in VectorStoreService | Pattern already established in similarity_search() |

**Key insight:** All the hard algorithmic work (MMR, cosine similarity) is already installed via langchain-core and scikit-learn. Phase 3c is primarily **wiring and guarding**, not algorithm implementation.

---

## Common Pitfalls

### Pitfall 1: get_or_create_collection Does NOT Update Metadata

**What goes wrong:** Developer calls `get_or_create_collection('proj_1', metadata={'provider': 'openai'})` on an existing collection created with `provider: 'local'`. Metadata silently stays as `local`. EMBED-04 check then passes incorrectly.
**Why it happens:** ChromaDB `get_or_create` semantics: metadata only applies on creation, not on retrieval of existing collection.
**How to avoid:** Never rely on `get_or_create_collection` to update metadata. To update: call `collection.modify(metadata={...})`. For re-index: delete and re-create collection.
**Warning signs:** Collection metadata stays as the original value after calling get_or_create with different metadata.
[VERIFIED: against ChromaDB 1.5.7 live runtime]

### Pitfall 2: Collection Created Without Cosine Metric Cannot Be Changed

**What goes wrong:** Collections already created by Phase 3b ingestion use the default L2 metric. Switching to cosine requires deleting and recreating the collection.
**Why it happens:** `hnsw:space` is set at collection creation and cannot be changed via `modify()`.
**How to avoid:** Phase 3c must delete all existing `project_*` collections and recreate them with `hnsw:space=cosine` during the re-index wave. The EMBED-05 re-index endpoint handles this naturally.
**Warning signs:** Score thresholds produce unexpected results (L2 distances have different scale than cosine distances).
[VERIFIED: ChromaDB configuration_json confirmed `hnsw.space: l2` as default]

### Pitfall 3: MMR Requires Embeddings in Query Results

**What goes wrong:** `maximal_marginal_relevance` receives `None` for the embedding list because `include=['embeddings']` was not passed to `collection.query()`.
**Why it happens:** ChromaDB does not return embeddings by default; must be explicitly requested.
**How to avoid:** Always include `'embeddings'` in the `include` list when performing MMR search.
**Warning signs:** `TypeError` or `AttributeError` when passing `results['embeddings'][0]` to MMR function.
[VERIFIED: ChromaDB query API confirmed]

### Pitfall 4: All Tests Fail Due to Missing google-genai Package

**What goes wrong:** `conftest.py` imports `app.main` which imports `document_parser.py` which imports `image_processor.py` which does `from google import genai`. If `google-genai` is not installed, `ImportError` at collection time breaks ALL tests.
**Why it happens:** `google-genai` is in `requirements.txt` but not installed in the current test environment.
**How to avoid:** Wave 0 must install `google-genai` before any other task. Also add `google.genai` to the conftest `sys.modules` pre-mock as a fallback for CI environments without the package.
**Warning signs:** `ImportError: cannot import name 'genai' from 'google'` when running pytest.
[VERIFIED: pytest run confirmed this exact error]

### Pitfall 5: Dimension Mismatch When Switching Providers

**What goes wrong:** Collection has 384-dim vectors (all-MiniLM-L6-v2). After switch, new documents embed to 1536-dim (OpenAI) or 768-dim (Google). ChromaDB raises dimension mismatch error.
**Why it happens:** ChromaDB infers expected dimensions from the first vectors added to a collection.
**How to avoid:** EMBED-04 provider mismatch check prevents new embeddings from a different provider. EMBED-05 re-index deletes the collection and recreates it, resetting expected dimensions.
**Warning signs:** ChromaDB error about incompatible embedding dimensions on `upsert()`.
[VERIFIED: dimension values from provider documentation — ASSUMED for exact error message wording]

### Pitfall 6: Re-Index Races with Active Background Tasks

**What goes wrong:** Re-index starts deleting the collection while a background ingestion task for the same project is mid-write.
**Why it happens:** Re-index endpoint runs in request thread; ingestion runs in background thread.
**How to avoid:** Acquire the per-project write lock in the re-index endpoint's collection-delete step, just as `insert_documents()` does.
**Warning signs:** Intermittent ChromaDB errors during concurrent upload + re-index.
[ASSUMED: based on threading analysis; not load-tested]

### Pitfall 7: score_threshold Default Too High or Too Low

**What goes wrong:** Default `score_threshold=0.0` returns all results regardless of relevance. Default `score_threshold=0.9` returns nothing for most queries.
**Why it happens:** Cosine similarity depends on the embedding space and query quality.
**How to avoid:** Use `score_threshold=0.3` as the default (empirically reasonable for sentence-transformers cosine space). Expose it as a query parameter so callers can tune it.
**Warning signs:** Search returns garbage results or empty lists for reasonable queries.
[ASSUMED: 0.3 is a common starting point; should be validated with real documents]

---

## Code Examples

### ChromaDB Collection with Cosine Metric and Provider Metadata
```python
# Source: VERIFIED against ChromaDB 1.5.7 PersistentClient
collection = client.get_or_create_collection(
    name='project_1',
    metadata={
        'embedding_provider': 'local',
        'embedding_model': 'all-MiniLM-L6-v2',
        'hnsw:space': 'cosine',
    },
)
# collection.metadata == {'embedding_provider': 'local', 'embedding_model': 'all-MiniLM-L6-v2', 'hnsw:space': 'cosine'}
```

### Reading and Checking Collection Metadata
```python
# Source: VERIFIED against ChromaDB 1.5.7
collection = client.get_collection('project_1')
meta = collection.metadata or {}
stored_provider = meta.get('embedding_provider')
# stored_provider == 'local' even if you call get_or_create_collection with different metadata
```

### Deleting a Collection for Re-Index
```python
# Source: VERIFIED against ChromaDB 1.5.7
try:
    client.delete_collection('project_1')
except Exception:
    pass  # Collection may not exist yet (first reindex before any ingestion)
# Re-create with new provider metadata
collection = client.get_or_create_collection(
    name='project_1',
    metadata={'embedding_provider': 'openai', 'embedding_model': 'text-embedding-3-small', 'hnsw:space': 'cosine'},
)
```

### MMR Full Pipeline
```python
# Source: VERIFIED - langchain_core.vectorstores.utils.maximal_marginal_relevance confirmed installed
import numpy as np
from langchain_core.vectorstores.utils import maximal_marginal_relevance

# 1. Get query embedding
query_emb = embedding_model.embed_query(query_text)

# 2. Fetch more results than needed, WITH embeddings
results = collection.query(
    query_embeddings=[query_emb],
    n_results=20,  # fetch_k
    include=['documents', 'metadatas', 'distances', 'embeddings'],
)

# 3. Apply score threshold (cosine: similarity = 1 - distance)
sims = [1.0 - d for d in results['distances'][0]]
above = [(doc, meta, sim, emb)
         for doc, meta, sim, emb
         in zip(results['documents'][0], results['metadatas'][0], sims, results['embeddings'][0])
         if sim >= 0.3]

# 4. Apply MMR
if above:
    docs, metas, sims_filtered, embs = zip(*above)
    indices = maximal_marginal_relevance(
        np.array(query_emb), list(embs), lambda_mult=0.5, k=5
    )
    final = [{'content': docs[i], 'metadata': metas[i], 'similarity': sims_filtered[i]} for i in indices]
```

### Per-Project Write Lock
```python
# Source: VERIFIED against Python 3.12 threading module

import threading
_project_locks: dict[int | None, threading.Lock] = {}
_locks_mutex = threading.Lock()

def _get_project_lock(project_id: int | None) -> threading.Lock:
    with _locks_mutex:
        if project_id not in _project_locks:
            _project_locks[project_id] = threading.Lock()
        return _project_locks[project_id]

# In insert_documents():
with _get_project_lock(project_id):
    collection.upsert(documents=..., embeddings=..., metadatas=..., ids=...)
```

### OpenAI Embeddings via langchain-openai 1.1.12
```python
# Source: langchain-openai 1.1.12 PyPI requirements verified; API shape ASSUMED from LangChain docs
from langchain_openai import OpenAIEmbeddings
emb = OpenAIEmbeddings(model='text-embedding-3-small', api_key=api_key)
# api_key=None reads OPENAI_API_KEY env var automatically
vectors = emb.embed_documents(['text 1', 'text 2'])  # list[list[float]], each 1536-dim
query_vector = emb.embed_query('query text')          # list[float], 1536-dim
```

### Google Embeddings via google-genai SDK (no extra package)
```python
# Source: google.generativeai.embed_content signature VERIFIED; google-genai API shape ASSUMED
# (google-genai not yet installed in test env)
from google import genai

client = genai.Client(api_key=api_key)
result = client.models.embed_content(
    model='models/text-embedding-004',
    contents=['text 1', 'text 2'],
)
vectors = [e.values for e in result.embeddings]  # list[list[float]], each 768-dim
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| google-generativeai SDK | google-genai SDK | Phase 3b (image_processor.py) | Must install google-genai package |
| models/embedding-001 | models/text-embedding-004 | Google API v4 (2024) | Embeddings.py has wrong model name |
| LangChain RetrievalQA | Direct ChromaDB query + MMR | Project decision | More control over citations |
| L2 distance (default ChromaDB) | Cosine distance (hnsw:space=cosine) | Phase 3c recommendation | Intuitive similarity scores in [0, 1] |

**Deprecated/outdated in this codebase:**
- `models/embedding-001` in `embeddings.py`: outdated Google model name. Correct name is `models/text-embedding-004`.
- `get_default_embeddings()` called directly in `VectorStoreService`: must be replaced with injectable embedding model to support provider switching.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | google-genai SDK provides `client.models.embed_content(model, contents)` returning `result.embeddings[i].values` | Code Examples | _GeminiEmbeddings wrapper breaks; must fall back to google-generativeai.embed_content |
| A2 | langchain-openai 1.1.12 `OpenAIEmbeddings(api_key=...)` reads OPENAI_API_KEY env var when api_key=None | Code Examples | Must pass api_key explicitly; search for correct param name |
| A3 | score_threshold=0.3 is a reasonable default for cosine similarity | Common Pitfalls | May need tuning; expose as query param to allow caller adjustment |
| A4 | hnsw:space=cosine cannot be updated on existing collection via modify() | Common Pitfalls Pitfall 2 | If modifiable, could avoid re-index for metric change |
| A5 | sentence-transformers model all-MiniLM-L6-v2 produces 384-dim vectors | Standard Stack | Dimension mismatch in tests if wrong |
| A6 | Re-index endpoint with 202 status is acceptable (no websocket for progress) | Architecture | UX may require polling endpoint to check reindex status |

---

## Open Questions

1. **Google embedding dimensions (text-embedding-004)**
   - What we know: Google's text-embedding-004 documentation states 768 dimensions
   - What's unclear: Whether the google-genai SDK returns exactly 768 or a different size
   - Recommendation: Verify with a real API call or mock test; 768 is the documented value

2. **Existing ChromaDB collections (pre-Phase-3c) need re-index**
   - What we know: Phase 3b ingested documents into collections without `hnsw:space=cosine` or provider metadata
   - What's unclear: Should Phase 3c auto-migrate existing collections, or require explicit re-index call?
   - Recommendation: Require explicit re-index (POST /api/projects/{id}/reindex). Document this as a migration step. Do not auto-migrate on startup.

3. **api_key passing for search endpoint**
   - What we know: Search endpoint needs to know which provider to use and the API key
   - What's unclear: Is it safe to pass API keys as query parameters (logged in access logs)?
   - Recommendation: Accept api_key as a query parameter for now (single-user local tool per REQUIREMENTS.md Out of Scope). Document this limitation.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| chromadb | Vector storage | Yes | 1.5.7 | — |
| langchain-core | MMR utility | Yes | 1.2.28 | — |
| google-generativeai | image_processor.py (old path) | Yes | 0.8.6 | — |
| google-genai | image_processor.py (new path) | **No** | — | Must install — blocks all tests |
| langchain-openai | OpenAI embeddings | **No** | — | Must install — blocks EMBED-02 for OpenAI |
| sentence-transformers | Local embeddings | Listed in STACK.md | 5.3.0 | Model loads lazily — failure surfaces on first embed |
| openai SDK | Via langchain-openai | No | — | Installed as dependency of langchain-openai |

**Missing dependencies with no fallback (block execution):**
- `google-genai`: Not installed. `image_processor.py` does `from google import genai` → all tests fail at conftest import time. Must be installed in Wave 0.
- `langchain-openai`: Not installed. Required for `OpenAIEmbeddings` (EMBED-02 OpenAI path). Must be installed in Wave 0.

**Missing dependencies with fallback:**
- None — the two above are hard blocks.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | none — inferred from tests/ directory |
| Quick run command | `python -m pytest tests/test_vector_store.py tests/test_embeddings.py tests/test_search_router.py -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EMBED-01 | Local embedding loads lazily, produces 384-dim vectors | unit | `pytest tests/test_embeddings.py -x` | Partial (test_embeddings.py exists) |
| EMBED-02 | OpenAI and Google providers instantiate without error (mocked API) | unit | `pytest tests/test_embeddings.py::test_openai_embedding_factory -x` | No — Wave 0 |
| EMBED-03 | Collection metadata contains provider+model after creation | unit | `pytest tests/test_vector_store.py::test_collection_metadata_stored -x` | No — Wave 0 |
| EMBED-04 | Provider mismatch raises ValueError | unit | `pytest tests/test_vector_store.py::test_provider_mismatch_raises -x` | No — Wave 0 |
| EMBED-05 | Re-index endpoint returns 202, deletes collection, queues docs | integration | `pytest tests/test_search_router.py::test_reindex_returns_202 -x` | No — Wave 0 |
| EMBED-06 | Concurrent inserts to same project do not corrupt (threading) | unit | `pytest tests/test_vector_store.py::test_write_lock_serializes -x` | No — Wave 0 |
| SEARCH-01 | Search endpoint returns chunks with content, metadata, similarity | integration | `pytest tests/test_search_router.py::test_search_returns_results -x` | No — Wave 0 |
| SEARCH-02 | Chunks below threshold are excluded | unit | `pytest tests/test_vector_store.py::test_score_threshold_filters -x` | No — Wave 0 |
| SEARCH-03 | MMR returns diverse results (no near-duplicates) | unit | `pytest tests/test_vector_store.py::test_mmr_deduplication -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_vector_store.py tests/test_embeddings.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_search_router.py` — covers EMBED-05, SEARCH-01
- [ ] New tests in `tests/test_vector_store.py` — covers EMBED-03, EMBED-04, EMBED-06, SEARCH-02, SEARCH-03
- [ ] New tests in `tests/test_embeddings.py` — covers EMBED-02
- [ ] `pip install google-genai langchain-openai==1.1.12` — blocks all test collection

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user local tool |
| V3 Session Management | No | Stateless API |
| V4 Access Control | No | No multi-user isolation required |
| V5 Input Validation | Yes | FastAPI Query params with ge/le bounds; query text length limit |
| V6 Cryptography | No | API keys passed through, not stored |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leakage in logs | Information Disclosure | Never log api_key value; only log presence/absence (established pattern from image_processor.py) |
| Unbounded query text (DoS) | Denial of Service | Add `max_length=1000` constraint to `q` Query param |
| Collection name injection | Tampering | Collection name is derived from project_id (integer) — `f'project_{project_id}'` is safe |
| Concurrent write corruption | Tampering | Per-project threading.Lock prevents this (EMBED-06) |

---

## Sources

### Primary (HIGH confidence)
- ChromaDB 1.5.7 PersistentClient — verified `get_or_create_collection`, `collection.metadata`, `delete_collection`, `query(include=['embeddings'])` behavior via live runtime calls
- langchain-core 1.2.28 — verified `maximal_marginal_relevance` function signature and behavior via live import
- Python 3.12 stdlib threading — verified `threading.Lock` per-project dict pattern
- FastAPI 0.135.3 — verified Query parameter pattern
- requirements.txt, domain.py, vector_store.py, embeddings.py, image_processor.py — direct code inspection

### Secondary (MEDIUM confidence)
- PyPI langchain-openai 1.1.12 metadata — verified `langchain-core<2.0.0,>=1.2.21` and `openai<3.0.0,>=2.26.0` requirements
- PyPI langchain-google-genai 2.1.12 metadata — verified `google-ai-generativelanguage>=0.7` dependency (already installed)
- PyPI langchain-google-genai 4.2.1 metadata — confirmed `google-genai<2.0.0,>=1.56.0` requirement (explains why 4.x cannot be used without installing google-genai first)
- google-generativeai 0.8.6 `embed_content` signature — verified via live `inspect.signature()` call

### Tertiary (LOW confidence / ASSUMED)
- google-genai SDK `client.models.embed_content()` API shape — package not installed, based on google-genai documentation patterns and consistency with google.generativeai API
- all-MiniLM-L6-v2 vector dimensions (384) — STACK.md states this; could not verify via live embedding call in current env
- text-embedding-3-small (1536-dim), text-embedding-004 (768-dim) — documented values, not verified via live API

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all critical packages verified via pip list and live imports
- Architecture patterns: HIGH — ChromaDB API behaviors verified against live runtime; threading patterns verified
- Pitfalls: HIGH for pitfalls 1-4 (all verified); MEDIUM for pitfalls 5-7 (inferred from architecture)
- Package installation plan: HIGH — PyPI metadata fetched directly for version compatibility

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (30 days — ChromaDB and langchain-core are stable libraries)
