"""
ImageProcessorService — summarizes document images via Gemini Vision API.

Design decisions implemented:
  D-05: ImageProcessorService class with summarize_image() public interface
  D-06: API key validated at call time, not at import/startup
  D-07: Missing key → placeholder text, no exception raised
  D-08: API key never logged; only presence/absence is logged

Threat mitigations:
  T-3b-03: API key value never appears in any log message
  T-3b-04: tenacity stop_after_attempt(3) caps retries; placeholder returned on final failure
"""

import logging
import os
from pathlib import Path

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

PLACEHOLDER_TEMPLATE = "[Image: unable to process - {filename}]"


class ImageProcessorService:
    """Summarizes document images via Gemini Vision API. Per D-05, D-06, D-07, D-08."""

    def summarize_image(self, image_path: str, filename: str) -> str:
        """
        Summarize an image using Gemini Vision API.

        Returns summary text on success, placeholder string on any failure.
        API key is validated at call time, not at startup (per D-06, D-07).
        """
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            # Log only presence/absence — never the key value (T-3b-03)
            logger.warning("GOOGLE_API_KEY not set — using placeholder for %s", filename)
            return PLACEHOLDER_TEMPLATE.format(filename=filename)

        return self._summarize_with_retry(image_path, filename, api_key)

    def _summarize_with_retry(self, image_path: str, filename: str, api_key: str) -> str:
        """Attempt Gemini call with retries; return placeholder on final failure."""
        try:
            return self._call_gemini(image_path, api_key)
        except Exception as exc:
            # Log the error detail but NOT the api_key (T-3b-03)
            logger.warning(
                "Gemini Vision failed after retries for %s: %s",
                filename,
                exc,
            )
            return PLACEHOLDER_TEMPLATE.format(filename=filename)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    def _call_gemini(self, image_path: str, api_key: str) -> str:
        """
        Call Gemini Vision API with inline image bytes (not Files API).

        Decorated with tenacity retry: up to 3 attempts with exponential backoff
        (2s, 4s, 8s). reraise=True ensures the final exception propagates to
        _summarize_with_retry which converts it to a placeholder (T-3b-04).
        """
        client = genai.Client(api_key=api_key)
        image_bytes = Path(image_path).read_bytes()

        # Determine MIME type from file extension (unstructured typically exports PNG)
        ext = Path(image_path).suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_map.get(ext, "image/png")

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                "Describe this image concisely for use in a document search system. "
                "Focus on key visual elements, text visible in the image, and subject matter.",
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        )
        return response.text
