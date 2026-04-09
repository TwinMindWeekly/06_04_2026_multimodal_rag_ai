---
phase: 03C-retrieval
plan: "02"
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/services/vector_store.py
  - backend/tests/test_vector_store.py
autonomous: true
requirements: [EMBED-03, EMBED-04, EMBED-06, SEARCH-02, SEARCH-03]
must_haves:
  truths:
    - "New collections are created with embedding_provider and embedding_model in ChromaDB metadata"
    - "New collections use hnsw:space=cosine for intuitive similarity scoring"
    - "Querying a collection with a different provider than what created it raises a clear error"
    - "Concurrent writes to the same project are serialized via per-project threading.Lock"
    - "Search results below score_threshold are excluded"
    - "MMR deduplication returns diverse results from overlapping chunks"
  artifacts:
    - path: "backend/app/services/vector_store.py"
      provides: "Extended VectorStoreService with provider metadata, mismatch guard, write lock, MMR search"
      exports: ["VectorStoreService", "_sanitize_metadata", "_get_project_lock"]
    - path: "backend/tests/test_vector_store.py"
      provides: "Tests for collection metadata, provider mismatch, write lock, score threshold, MMR"
      contains: "test_collection_metadata_stored"
  key_links:
    - from: "backend/app/services/vector_store.py"
      to: "chromadb.PersistentClient"
      via: "get_or_create_collection with metadata"
      pattern: "embedding_provider.*embedding_model.*hnsw:space"
    - from: "backend/app/services/vector_store.py"
      to: "langchain_core.vectorstores.utils.maximal_marginal_relevance"
      via: "import in similarity_search_mmr"
      pattern: "maximal_marginal_relevance"
    - from: "backend/app/services/vector_store.py"
      to: "threading.Lock"
      via: "_get_project_lock helper"
      pattern: "_project_locks.*threading\\.Lock"
---

<objective>
Extend VectorStoreService with collection metadata tracking, provider mismatch detection, per-project write locks, score threshold filtering, and MMR deduplication.

Purpose: EMBED-03 requires provider metadata on collections. EMBED-04 requires mismatch blocking. EMBED-06 requires write serialization. SEARCH-02 requires score filtering. SEARCH-03 requires MMR diversity. These are all VectorStoreService-internal changes that don't require the search router (Plan 03).

Output: Extended vector_store.py with 5 new capabilities and comprehensive tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/03C-retrieval/03C-RESEARCH.md

<interfaces>
<!-- Current VectorStoreService interface (to be extended) -->
From backend/app/services/vector_store.py:
```python
def _sanitize_metadata(meta: dict) -> dict: ...  # module-level, keep as-is

class VectorStoreService:
    def __init__(self): self.client = PersistentClient(path=CHROMADB_DIR)
    def _get_collection_name(self, project_id: int): ...
    def insert_documents(self, text_chunks, metadatas, project_id=None): ...
    def delete_by_document(self, document_id, project_id=None): ...
    def similarity_search(self, query, top_k=4, project_id=None): ...

vector_store = VectorStoreService()  # module-level singleton
```

<!-- EmbeddingFactory interface (consumed by this plan) -->
From backend/app/services/embeddings.py (after Plan 01):
```python
class EmbeddingFactory:
    @staticmethod
    def get_embedding_model(provider: str = 'local', api_key: str | None = None): ...

def get_default_embeddings(): ...  # lazy singleton for 'local' provider
```

<!-- MMR utility (already installed, no new dep) -->
From langchain_core.vectorstores.utils:
```python
def maximal_marginal_relevance(
    query_embedding: np.ndarray,
    embedding_list: list,
    lambda_mult: float = 0.5,
    k: int = 4
) -> list[int]: ...  # returns indices into embedding_list
```

<!-- ChromaDB Collection API (verified in RESEARCH.md) -->
```python
collection = client.get_or_create_collection(name=..., metadata={...})
collection.metadata  # dict, set only on first creation
collection.query(query_embeddings=[...], n_results=N, include=['documents', 'metadatas', 'distances', 'embeddings'])
collection.count()  # int
collection.delete(where={...})
client.delete_collection(name)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add per-project write lock + collection metadata + provider mismatch check</name>
  <files>backend/app/services/vector_store.py, backend/tests/test_vector_store.py</files>
  <read_first>
    - backend/app/services/vector_store.py
    - backend/tests/test_vector_store.py
    - backend/app/services/embeddings.py (to understand get_default_embeddings import)
  </read_first>
  <behavior>
    - test_collection_metadata_stored: Create a collection via insert_documents with provider='local', model='all-MiniLM-L6-v2'. Read collection.metadata. Assert 'embedding_provider'=='local', 'embedding_model'=='all-MiniLM-L6-v2', 'hnsw:space'=='cosine'.
    - test_provider_mismatch_raises: Create collection with provider='local'. Call _check_provider_match with active_provider='openai'. Assert raises ValueError containing 'mismatch'.
    - test_provider_match_passes: Create collection with provider='local'. Call _check_provider_match with active_provider='local'. Assert no exception.
    - test_write_lock_serializes: Use threading to run 2 concurrent insert_documents on same project_id. Assert both complete without error (lock serializes them). Verify _get_project_lock returns same Lock for same project_id.
    - test_write_lock_different_projects: _get_project_lock(1) is not _get_project_lock(2) (different locks).
    - test_insert_documents_uses_lock: Patch _get_project_lock, call insert_documents. Assert lock was acquired (context manager entered).
  </behavior>
  <action>
1. **Write tests first** in `backend/tests/test_vector_store.py`. Keep all 6 existing tests. Add 6 new tests below them.

   All tests that need a real ChromaDB should use `tempfile.mkdtemp()` + `PersistentClient(path=tmpdir)` pattern (already established in `test_delete_by_document_no_collection_no_error`).

   - `test_collection_metadata_stored`: Create VectorStoreService with temp dir. Mock `get_default_embeddings` to return mock embedding model (mock.embed_documents returns [[0.1]*384]). Call `insert_documents(['text'], [{'document_id': '1', 'filename': 'test.pdf'}], project_id=1, provider='local', model='all-MiniLM-L6-v2')`. Get collection via `svc.client.get_collection('project_1')`. Assert `collection.metadata['embedding_provider'] == 'local'` and `collection.metadata['embedding_model'] == 'all-MiniLM-L6-v2'` and `collection.metadata['hnsw:space'] == 'cosine'`.

   - `test_provider_mismatch_raises`: Create a collection manually with `metadata={'embedding_provider': 'local'}`. Call `svc._check_provider_match(collection, 'openai')`. Assert `pytest.raises(ValueError, match='mismatch')`.

   - `test_provider_match_passes`: Same setup, call `svc._check_provider_match(collection, 'local')`. No exception.

   - `test_write_lock_serializes`: Import `_get_project_lock` from vector_store. Call it twice with `project_id=1`. Assert both return the same Lock object. Call with `project_id=2`. Assert different Lock.

   - `test_write_lock_different_projects`: `_get_project_lock(1) is not _get_project_lock(2)`.

   - `test_insert_documents_uses_lock`: Patch `app.services.vector_store._get_project_lock` to return a MagicMock lock. Call `insert_documents(...)`. Assert `lock.__enter__` was called (context manager used).

2. Run tests — they should FAIL (RED).

3. **Implement** in `backend/app/services/vector_store.py`:

   a. Add imports at top:
      ```python
      import threading
      import numpy as np
      ```

   b. Add per-project lock infrastructure after `CHROMADB_DIR` setup (before the class):
      ```python
      _project_locks: dict[int | None, threading.Lock] = {}
      _locks_mutex: threading.Lock = threading.Lock()


      def _get_project_lock(project_id: int | None) -> threading.Lock:
          """Return a per-project threading.Lock, creating if needed."""
          with _locks_mutex:
              if project_id not in _project_locks:
                  _project_locks[project_id] = threading.Lock()
              return _project_locks[project_id]
      ```

   c. Add `_check_provider_match` method to VectorStoreService:
      ```python
      def _check_provider_match(self, collection, active_provider: str) -> None:
          """Raise ValueError if active provider mismatches collection's stored provider (EMBED-04)."""
          stored = (collection.metadata or {}).get('embedding_provider')
          if stored and stored != active_provider:
              raise ValueError(
                  f'Embedding provider mismatch: collection uses "{stored}", '
                  f'active provider is "{active_provider}". Re-index to switch providers.'
              )
      ```

   d. Modify `insert_documents` signature to accept embedding_model, provider, model:
      ```python
      def insert_documents(
          self,
          text_chunks: list[str],
          metadatas: list[dict],
          project_id: int | None = None,
          embedding_model=None,
          provider: str = 'local',
          model: str = 'all-MiniLM-L6-v2',
      ) -> None:
      ```

   e. Replace the `get_or_create_collection` call in `insert_documents` to include metadata:
      ```python
      collection_name = self._get_collection_name(project_id)
      collection = self.client.get_or_create_collection(
          name=collection_name,
          metadata={
              'embedding_provider': provider,
              'embedding_model': model,
              'hnsw:space': 'cosine',
          },
      )
      ```

   f. Replace `get_default_embeddings()` call with injectable embedding_model:
      ```python
      emb = embedding_model or get_default_embeddings()
      embeddings = emb.embed_documents(text_chunks)
      ```

   g. Wrap the `collection.upsert(...)` call in the per-project lock:
      ```python
      with _get_project_lock(project_id):
          collection.upsert(
              documents=text_chunks,
              embeddings=embeddings,
              metadatas=[_sanitize_metadata(m) for m in metadatas],
              ids=ids,
          )
      ```

   h. Similarly update `similarity_search` to accept `embedding_model` parameter and use it instead of `get_default_embeddings()` directly:
      ```python
      def similarity_search(self, query: str, top_k: int = 4, project_id: int | None = None, embedding_model=None):
          ...
          emb = embedding_model or get_default_embeddings()
          query_embedding = emb.embed_query(query)
          ...
      ```

4. Run tests — they should PASS (GREEN).
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/TwinMindWeekly/06_04_2026_multimodal_rag_ai && backend/.venv/Scripts/python -m pytest backend/tests/test_vector_store.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - grep "embedding_provider" backend/app/services/vector_store.py returns matches
    - grep "embedding_model" backend/app/services/vector_store.py returns matches
    - grep "hnsw:space.*cosine" backend/app/services/vector_store.py returns a match
    - grep "_check_provider_match" backend/app/services/vector_store.py returns matches
    - grep "_get_project_lock" backend/app/services/vector_store.py returns matches
    - grep "_project_locks" backend/app/services/vector_store.py returns matches
    - grep "threading.Lock" backend/app/services/vector_store.py returns matches
    - grep "test_collection_metadata_stored" backend/tests/test_vector_store.py returns a match
    - grep "test_provider_mismatch_raises" backend/tests/test_vector_store.py returns a match
    - grep "test_write_lock_serializes" backend/tests/test_vector_store.py returns a match
    - pytest backend/tests/test_vector_store.py -x -v shows 12 tests passed (6 existing + 6 new)
  </acceptance_criteria>
  <done>VectorStoreService stores provider metadata on collection creation. _check_provider_match raises ValueError on mismatch. Per-project write lock serializes concurrent writes. insert_documents and similarity_search accept injectable embedding_model. All 12 vector store tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add similarity_search_mmr with score threshold + MMR deduplication</name>
  <files>backend/app/services/vector_store.py, backend/tests/test_vector_store.py</files>
  <read_first>
    - backend/app/services/vector_store.py (after Task 1 changes)
    - backend/tests/test_vector_store.py (after Task 1 changes)
  </read_first>
  <behavior>
    - test_score_threshold_filters: Query results with distances [0.1, 0.5, 0.9] (cosine). With score_threshold=0.6 (similarity >= 0.6 means distance <= 0.4), only the first result (distance 0.1, sim 0.9) passes.
    - test_mmr_deduplication: 5 results with 3 near-duplicate embeddings. MMR with top_k=3 selects diverse subset.
    - test_similarity_search_mmr_empty_collection: Empty collection returns [].
    - test_similarity_search_mmr_returns_format: Each result has keys: 'content', 'metadata', 'similarity', 'distance'.
    - test_similarity_search_mmr_provider_check: Call with active provider different from collection metadata. Assert raises ValueError.
  </behavior>
  <action>
1. **Write tests first** in `backend/tests/test_vector_store.py`. Add 5 new tests after existing ones.

   For MMR tests, use a temp ChromaDB directory with PersistentClient. Insert known documents with known embeddings. Query and verify filtering/deduplication.

   - `test_score_threshold_filters`: Create a VectorStoreService with temp dir. Insert 3 documents with mock embeddings. Mock the collection.query to return distances [0.1, 0.5, 0.9]. Call `similarity_search_mmr(query='test', score_threshold=0.6, project_id=1, embedding_model=mock_emb)`. Only results with similarity >= 0.6 (distance <= 0.4) should be returned.

   - `test_mmr_deduplication`: Patch `collection.query` to return 5 results with embeddings where 3 are near-identical. Call `similarity_search_mmr(top_k=3, lambda_mult=0.5)`. Assert returned results are diverse (not all from the same cluster). Can also verify that `maximal_marginal_relevance` was called.

   - `test_similarity_search_mmr_empty_collection`: Call on non-existent collection. Assert returns `[]`.

   - `test_similarity_search_mmr_returns_format`: Call with valid data. Assert each result dict has exactly keys: `content`, `metadata`, `similarity`, `distance`.

   - `test_similarity_search_mmr_provider_check`: Create collection with provider='local'. Call `similarity_search_mmr(..., provider='openai')`. Assert raises ValueError matching 'mismatch'.

2. Run tests — they should FAIL (RED).

3. **Implement** `similarity_search_mmr` method in VectorStoreService:

   ```python
   def similarity_search_mmr(
       self,
       query: str,
       top_k: int = 5,
       fetch_k: int = 20,
       score_threshold: float = 0.3,
       lambda_mult: float = 0.5,
       project_id: int | None = None,
       embedding_model=None,
       provider: str = 'local',
   ) -> list[dict]:
       """Semantic search with score filtering and MMR deduplication.

       SEARCH-01: Returns Top-K chunks with distances and metadata.
       SEARCH-02: Filters out chunks below score_threshold.
       SEARCH-03: Applies MMR to reduce near-duplicate results.
       """
       from langchain_core.vectorstores.utils import maximal_marginal_relevance

       collection_name = self._get_collection_name(project_id)
       try:
           collection = self.client.get_collection(name=collection_name)
       except Exception:
           return []

       # EMBED-04: check provider matches collection
       self._check_provider_match(collection, provider)

       emb = embedding_model or get_default_embeddings()
       query_embedding = emb.embed_query(query)

       # Fetch fetch_k results WITH embeddings (required for MMR)
       count = collection.count()
       if count == 0:
           return []

       results = collection.query(
           query_embeddings=[query_embedding],
           n_results=min(fetch_k, count),
           include=['documents', 'metadatas', 'distances', 'embeddings'],
       )

       if not results['documents'] or not results['documents'][0]:
           return []

       docs = results['documents'][0]
       metadatas_list = results['metadatas'][0]
       distances = results['distances'][0]
       embeddings_list = results['embeddings'][0]

       # SEARCH-02: cosine distance -> similarity, apply threshold
       # cosine distance: 0=identical, 2=opposite; similarity = 1 - distance
       above_threshold = []
       for doc, meta, dist, emb_vec in zip(docs, metadatas_list, distances, embeddings_list):
           sim = 1.0 - dist
           if sim >= score_threshold:
               above_threshold.append((doc, meta, sim, emb_vec))

       if not above_threshold:
           return []

       filtered_docs, filtered_metas, filtered_sims, filtered_embs = zip(*above_threshold)

       # SEARCH-03: MMR deduplication
       query_arr = np.array(query_embedding)
       selected_indices = maximal_marginal_relevance(
           query_arr, list(filtered_embs), lambda_mult=lambda_mult, k=min(top_k, len(filtered_docs)),
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

   Ensure `import numpy as np` is already at top (added in Task 1).

4. Run tests — they should PASS (GREEN).
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/TwinMindWeekly/06_04_2026_multimodal_rag_ai && backend/.venv/Scripts/python -m pytest backend/tests/test_vector_store.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - grep "def similarity_search_mmr" backend/app/services/vector_store.py returns a match
    - grep "score_threshold" backend/app/services/vector_store.py returns matches
    - grep "maximal_marginal_relevance" backend/app/services/vector_store.py returns a match
    - grep "from langchain_core.vectorstores.utils import maximal_marginal_relevance" backend/app/services/vector_store.py returns a match
    - grep "1.0 - dist" backend/app/services/vector_store.py returns a match (cosine distance to similarity conversion)
    - grep "test_score_threshold_filters" backend/tests/test_vector_store.py returns a match
    - grep "test_mmr_deduplication" backend/tests/test_vector_store.py returns a match
    - grep "test_similarity_search_mmr_empty_collection" backend/tests/test_vector_store.py returns a match
    - grep "test_similarity_search_mmr_returns_format" backend/tests/test_vector_store.py returns a match
    - grep "test_similarity_search_mmr_provider_check" backend/tests/test_vector_store.py returns a match
    - pytest backend/tests/test_vector_store.py -x -v shows 17 tests passed (12 from Task 1 + 5 new)
  </acceptance_criteria>
  <done>similarity_search_mmr method implements score threshold filtering (SEARCH-02) and MMR deduplication (SEARCH-03) with provider mismatch check (EMBED-04). Returns results as list of dicts with content, metadata, similarity, distance. All 17 vector store tests pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| caller -> VectorStoreService | query text, project_id, provider params cross boundary |
| VectorStoreService -> ChromaDB | collection operations with metadata |
| VectorStoreService -> EmbeddingFactory | embedding model used for query embedding |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-3c-04 | Tampering | collection metadata | mitigate | get_or_create_collection sets metadata only on first creation (verified in RESEARCH.md). _check_provider_match validates on every query. |
| T-3c-05 | Denial of Service | similarity_search_mmr | mitigate | fetch_k capped at min(fetch_k, collection.count()) prevents unbounded memory. top_k has ge=1, le=20 constraint (applied in Plan 03 router). |
| T-3c-06 | Tampering | concurrent write corruption | mitigate | Per-project threading.Lock via _get_project_lock serializes all upsert calls per collection (EMBED-06). |
| T-3c-07 | Information Disclosure | similarity_search_mmr | accept | Returns stored chunk content + metadata to caller. Single-user local tool; no cross-tenant data leakage concern. |
</threat_model>

<verification>
1. `backend/.venv/Scripts/python -m pytest backend/tests/test_vector_store.py -x -v` — all 17 tests pass
2. `backend/.venv/Scripts/python -m pytest backend/tests/ -x -q` — full suite green
3. `grep "_check_provider_match" backend/app/services/vector_store.py` — method exists
4. `grep "similarity_search_mmr" backend/app/services/vector_store.py` — method exists
5. `grep "_get_project_lock" backend/app/services/vector_store.py` — function exists
</verification>

<success_criteria>
- Collections created with embedding_provider, embedding_model, hnsw:space=cosine metadata
- Provider mismatch raises ValueError with clear message
- Per-project write lock prevents concurrent ChromaDB corruption
- similarity_search_mmr filters by score threshold and deduplicates via MMR
- 17 vector store tests pass (6 existing + 6 Task 1 + 5 Task 2)
- Full test suite green
</success_criteria>

<output>
After completion, create `.planning/phases/03C-retrieval/03C-02-SUMMARY.md`
</output>
