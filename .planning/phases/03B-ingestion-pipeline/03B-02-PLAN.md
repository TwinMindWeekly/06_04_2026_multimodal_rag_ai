---
phase: 03B-ingestion-pipeline
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/services/image_processor.py
  - backend/tests/test_image_processor.py
autonomous: true
requirements: [PARSE-03, PARSE-04]

must_haves:
  truths:
    - "ImageProcessorService summarizes an image via Gemini Vision API with retry logic"
    - "Missing GOOGLE_API_KEY returns placeholder text, not an exception"
    - "After 3 retries with exponential backoff, final failure returns placeholder text"
    - "API key is never logged — only presence/absence is logged"
    - "Gemini is called with inline bytes, not Files API"
  artifacts:
    - path: "backend/app/services/image_processor.py"
      provides: "ImageProcessorService class"
      contains: "class ImageProcessorService"
    - path: "backend/tests/test_image_processor.py"
      provides: "Tests for PARSE-03, PARSE-04"
      contains: "test_summarize_success"
  key_links:
    - from: "backend/app/services/image_processor.py"
      to: "google-generativeai"
      via: "genai.GenerativeModel('gemini-1.5-pro-latest').generate_content()"
      pattern: "genai\\.GenerativeModel"
    - from: "backend/app/services/image_processor.py"
      to: "tenacity"
      via: "@retry decorator with stop_after_attempt(3) and wait_exponential"
      pattern: "@retry"
---

<objective>
Create the ImageProcessorService that summarizes extracted document images via Gemini Vision API with retry logic and graceful failure handling.

Purpose: The ingestion pipeline (Plan 03) needs image summarization to convert extracted images into searchable text chunks. This service is independently testable with mocked Gemini calls.

Output: A new `image_processor.py` service and comprehensive test file.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/03B-ingestion-pipeline/03B-CONTEXT.md
@.planning/phases/03B-ingestion-pipeline/03B-RESEARCH.md

<interfaces>
<!-- No existing file — this is a new service -->
<!-- Consumed by process_and_update_document() in document_parser.py (Plan 03) -->
<!-- Expected interface: -->
```python
class ImageProcessorService:
    def summarize_image(self, image_path: str, filename: str) -> str:
        """Returns summary text or placeholder on failure."""
        ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create ImageProcessorService with Gemini Vision + tenacity retry</name>
  <files>backend/app/services/image_processor.py, backend/tests/test_image_processor.py</files>
  <read_first>
    - backend/app/services/embeddings.py (for project singleton/factory pattern reference)
    - backend/app/services/document_parser.py (to understand how it will call this service)
    - backend/tests/conftest.py (for existing test fixtures pattern)
  </read_first>
  <behavior>
    - Test 1 (test_summarize_success): Mock genai.GenerativeModel to return a response with .text = "A chart showing revenue growth". Call summarize_image("/fake/path.png", "chart.png"). Assert returns "A chart showing revenue growth".
    - Test 2 (test_summarize_failure_returns_placeholder): Mock genai.GenerativeModel.generate_content to raise Exception on all 3 attempts. Call summarize_image("/fake/path.png", "chart.png"). Assert returns "[Image: unable to process - chart.png]".
    - Test 3 (test_missing_api_key_returns_placeholder): Ensure GOOGLE_API_KEY is unset (monkeypatch.delenv). Call summarize_image("/fake/path.png", "photo.png"). Assert returns "[Image: unable to process - photo.png]".
    - Test 4 (test_api_key_not_logged): Mock logger, call summarize_image with missing key. Assert no log message contains the actual value of any API key — only "GOOGLE_API_KEY not set" is acceptable.
    - Test 5 (test_retry_count): Mock generate_content to fail twice then succeed on third call. Assert returns the success text, and generate_content was called exactly 3 times.
  </behavior>
  <action>
**backend/app/services/image_processor.py** — Create new file implementing ImageProcessorService per D-05, D-06, D-07, D-08:

```python
import os
import logging
from pathlib import Path

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

PLACEHOLDER_TEMPLATE = "[Image: unable to process - {filename}]"


class ImageProcessorService:
    """Summarizes document images via Gemini Vision API. Per D-05, D-06, D-07, D-08."""

    def summarize_image(self, image_path: str, filename: str) -> str:
        """
        Summarize an image using Gemini Vision API.

        Returns summary text on success, placeholder string on any failure.
        API key validated at call time, not at startup (per D-07).
        """
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set — using placeholder for %s", filename)
            return PLACEHOLDER_TEMPLATE.format(filename=filename)

        genai.configure(api_key=api_key)

        result = self._summarize_with_retry(image_path, filename)
        return result

    def _summarize_with_retry(self, image_path: str, filename: str) -> str:
        """Attempt Gemini call with retries; return placeholder on final failure."""
        try:
            return self._call_gemini(image_path)
        except Exception as e:
            logger.warning("Gemini Vision failed after retries for %s: %s", filename, e)
            return PLACEHOLDER_TEMPLATE.format(filename=filename)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    def _call_gemini(self, image_path: str) -> str:
        """Call Gemini Vision API with inline image bytes. Retries on failure."""
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        image_bytes = Path(image_path).read_bytes()

        # Determine MIME type from extension (unstructured typically exports PNG)
        ext = Path(image_path).suffix.lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/png")

        response = model.generate_content([
            "Describe this image concisely for use in a document search system. "
            "Focus on key visual elements, text visible in the image, and subject matter.",
            {"mime_type": mime_type, "data": image_bytes},
        ])
        return response.text
```

**backend/tests/test_image_processor.py** — Create new test file with 5 tests:

Write the 5 test functions described in the behavior block above. Use `unittest.mock.patch` to mock `google.generativeai` module and `os.getenv`. Use `monkeypatch.delenv("GOOGLE_API_KEY", raising=False)` for the missing key test. For the retry count test, use `side_effect=[Exception("err"), Exception("err"), mock_response]` on `generate_content`. Set `tenacity` retry wait to 0 in tests by patching `_call_gemini.retry.wait` to `wait_exponential(multiplier=0, min=0, max=0)` to avoid 2-8 second waits.
  </action>
  <verify>
    <automated>cd D:/workspaces/projects/multimodal_rag_ai/backend && python -m pytest tests/test_image_processor.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - backend/app/services/image_processor.py contains `class ImageProcessorService:`
    - backend/app/services/image_processor.py contains `def summarize_image(self, image_path: str, filename: str) -> str:`
    - backend/app/services/image_processor.py contains `@retry(` with `stop=stop_after_attempt(3)`
    - backend/app/services/image_processor.py contains `wait=wait_exponential(multiplier=1, min=2, max=8)`
    - backend/app/services/image_processor.py contains `PLACEHOLDER_TEMPLATE = "[Image: unable to process - {filename}]"`
    - backend/app/services/image_processor.py contains `os.getenv("GOOGLE_API_KEY")`
    - backend/app/services/image_processor.py does NOT contain any line that logs an API key value (no f-string or format with api_key variable in a logger call)
    - backend/app/services/image_processor.py contains `genai.GenerativeModel("gemini-1.5-pro-latest")`
    - backend/tests/test_image_processor.py contains `test_summarize_success`
    - backend/tests/test_image_processor.py contains `test_summarize_failure_returns_placeholder`
    - backend/tests/test_image_processor.py contains `test_missing_api_key_returns_placeholder`
    - backend/tests/test_image_processor.py contains `test_api_key_not_logged`
    - backend/tests/test_image_processor.py contains `test_retry_count`
    - `python -m pytest tests/test_image_processor.py -x` exits 0
  </acceptance_criteria>
  <done>ImageProcessorService created with Gemini Vision integration, tenacity retry (3 attempts, 2-4-8s backoff), graceful placeholder on missing key or final failure. 5 tests passing.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| image_path -> Gemini API | File bytes read from disk and sent to external API |
| GOOGLE_API_KEY env -> genai.configure | API key from environment passed to SDK |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-3b-03 | Information Disclosure | ImageProcessorService | mitigate | Never log API key value; log only "GOOGLE_API_KEY not set" presence check. No f-string with api_key in any logger call. |
| T-3b-04 | Denial of Service | _call_gemini | mitigate | tenacity stop_after_attempt(3) with wait_exponential caps retries; placeholder returned on final failure, pipeline continues |
| T-3b-05 | Tampering | image_path | accept | Image paths come from unstructured's temp dir (trusted internal source, not user input). Plan 03 validates path prefix. |
</threat_model>

<verification>
- `python -m pytest tests/test_image_processor.py -x -q` exits 0
- `grep -c "class ImageProcessorService" backend/app/services/image_processor.py` returns 1
- `grep -c "stop_after_attempt(3)" backend/app/services/image_processor.py` returns 1
</verification>

<success_criteria>
- ImageProcessorService.summarize_image() returns summary text on Gemini success
- Missing API key returns placeholder, logs warning, does not raise
- 3 retries with exponential backoff (2s, 4s, 8s) executed before giving up
- Final failure after retries returns placeholder "[Image: unable to process - {filename}]"
- API key value never appears in any log output
- All 5 tests pass
</success_criteria>

<output>
After completion, create `.planning/phases/03B-ingestion-pipeline/03B-02-SUMMARY.md`
</output>
