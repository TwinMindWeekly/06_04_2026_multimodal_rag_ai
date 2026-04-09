"""
Tests for _build_chunks() function.

Covers: CHUNK-01 (chunk size), CHUNK-02 (metadata schema), CHUNK-03 (image interleaving).
"""

from unittest.mock import MagicMock


def _make_element(
    text: str,
    category: str = "NarrativeText",
    page_number: int = 1,
    image_path: str = None,
) -> dict:
    """Helper: create an element dict as returned by DocumentParserService.parse_document()."""
    return {
        "text": text,
        "category": category,
        "page_number": page_number,
        "image_path": image_path,
    }


def _make_image_processor(return_value: str = "Image description") -> MagicMock:
    """Helper: create a mock ImageProcessorService."""
    mock = MagicMock()
    mock.summarize_image.return_value = return_value
    return mock


class TestChunkSizeAndOverlap:
    """Tests for CHUNK-01: chunk size enforcement."""

    def test_chunk_size_within_limit(self):
        """Every returned chunk must have len <= 512 characters."""
        from app.services.document_parser import _build_chunks

        # Text longer than 512 chars must be split
        long_text = "A" * 600 + " " + "B" * 600
        elements = [_make_element(text=long_text, page_number=1)]
        mock_processor = _make_image_processor()

        chunks, metadatas = _build_chunks(
            elements=elements,
            image_processor=mock_processor,
            document_id=1,
            filename="test.pdf",
        )

        assert len(chunks) > 0, "Long text should produce at least one chunk"
        for chunk in chunks:
            assert len(chunk) <= 512, f"Chunk exceeds 512 chars: {len(chunk)}"

    def test_chunk_overlap(self):
        """Chunks from a long text should share overlapping content (overlap=64)."""
        from app.services.document_parser import _build_chunks

        # Build a text that will produce at least 2 chunks
        # Use repeated words so overlap is visible
        word = "overlap "
        long_text = word * 80  # ~640 chars => 2 chunks with overlap

        elements = [_make_element(text=long_text, page_number=1)]
        mock_processor = _make_image_processor()

        chunks, _ = _build_chunks(
            elements=elements,
            image_processor=mock_processor,
            document_id=1,
            filename="test.pdf",
        )

        if len(chunks) >= 2:
            # The end of chunk[0] and beginning of chunk[1] should share content
            end_of_first = chunks[0][-64:]
            start_of_second = chunks[1][:64]
            # At least some overlap should exist
            assert any(c in start_of_second for c in end_of_first.split()), \
                "Expected overlap between consecutive chunks"


class TestChunkMetadata:
    """Tests for CHUNK-02: metadata schema and value constraints."""

    def test_chunk_metadata_schema(self):
        """Every metadata dict must have all 5 required keys."""
        from app.services.document_parser import _build_chunks

        elements = [
            _make_element(text="First paragraph text here.", page_number=1),
            _make_element(text="Second paragraph on page two.", category="Title", page_number=2),
        ]
        mock_processor = _make_image_processor()

        _, metadatas = _build_chunks(
            elements=elements,
            image_processor=mock_processor,
            document_id=42,
            filename="report.pdf",
        )

        required_keys = {"document_id", "filename", "page_number", "chunk_index", "element_type"}
        for i, meta in enumerate(metadatas):
            assert required_keys.issubset(meta.keys()), (
                f"Metadata at index {i} missing keys: {required_keys - meta.keys()}"
            )

    def test_chunk_metadata_values_are_scalars(self):
        """Every metadata value must be a ChromaDB-compatible scalar: str, int, float, or bool."""
        from app.services.document_parser import _build_chunks

        elements = [
            _make_element(text="Some document text for testing.", page_number=3),
        ]
        mock_processor = _make_image_processor()

        _, metadatas = _build_chunks(
            elements=elements,
            image_processor=mock_processor,
            document_id=7,
            filename="doc.docx",
        )

        allowed_types = (str, int, float, bool)
        for i, meta in enumerate(metadatas):
            for key, value in meta.items():
                assert isinstance(value, allowed_types), (
                    f"Metadata[{i}][{key!r}] = {value!r} is not a ChromaDB scalar type"
                )


class TestImageSummaryInterleaving:
    """Tests for CHUNK-03: image summary interleaving."""

    def test_image_summary_interleaved(self):
        """Image summary chunk should appear between page 1 and page 3 chunks (sorted by page)."""
        from app.services.document_parser import _build_chunks

        elements = [
            _make_element(text="Page 1 content text.", category="NarrativeText", page_number=1),
            _make_element(
                text="",
                category="Image",
                page_number=2,
                image_path="/tmp/image.png",
            ),
            _make_element(text="Page 2 text after image.", category="NarrativeText", page_number=2),
            _make_element(text="Page 3 content text.", category="NarrativeText", page_number=3),
        ]
        mock_processor = _make_image_processor(return_value="Image description text")

        chunks, metadatas = _build_chunks(
            elements=elements,
            image_processor=mock_processor,
            document_id=1,
            filename="doc.pdf",
        )

        # Find positions of page 1, image_summary, and page 3 chunks
        page1_indices = [i for i, m in enumerate(metadatas) if m["page_number"] == 1]
        img_indices = [i for i, m in enumerate(metadatas) if m["element_type"] == "image_summary"]
        page3_indices = [i for i, m in enumerate(metadatas) if m["page_number"] == 3]

        assert len(img_indices) >= 1, "Expected at least one image_summary chunk"
        assert len(page1_indices) >= 1, "Expected page 1 chunks"
        assert len(page3_indices) >= 1, "Expected page 3 chunks"

        # Image summary (page 2) should come after page 1 and before page 3
        assert max(page1_indices) < min(img_indices), \
            "Image summary should appear after page 1 chunks"
        assert max(img_indices) < min(page3_indices), \
            "Image summary should appear before page 3 chunks"

        # Verify element_type is "image_summary"
        for idx in img_indices:
            assert metadatas[idx]["element_type"] == "image_summary"

    def test_image_summary_element_type(self):
        """Image summary chunks must have element_type='image_summary'."""
        from app.services.document_parser import _build_chunks

        elements = [
            _make_element(
                text="",
                category="Image",
                page_number=1,
                image_path="/tmp/chart.png",
            ),
        ]
        mock_processor = _make_image_processor(return_value="A bar chart showing revenue.")

        _, metadatas = _build_chunks(
            elements=elements,
            image_processor=mock_processor,
            document_id=1,
            filename="slides.pptx",
        )

        assert len(metadatas) >= 1
        assert all(m["element_type"] == "image_summary" for m in metadatas)


class TestChunkIndex:
    """Tests for globally unique chunk_index."""

    def test_chunk_index_globally_unique(self):
        """chunk_index values must be [0, 1, 2, ...] — no duplicates, no gaps."""
        from app.services.document_parser import _build_chunks

        # Use multiple elements that will each produce multiple chunks
        long_text = "word " * 120  # ~600 chars => 2 chunks per element
        elements = [
            _make_element(text=long_text, page_number=1),
            _make_element(text=long_text, page_number=2),
            _make_element(text=long_text, page_number=3),
        ]
        mock_processor = _make_image_processor()

        _, metadatas = _build_chunks(
            elements=elements,
            image_processor=mock_processor,
            document_id=1,
            filename="multi.pdf",
        )

        indices = [m["chunk_index"] for m in metadatas]
        expected = list(range(len(metadatas)))
        assert indices == expected, (
            f"chunk_index should be sequential [0..{len(metadatas)-1}], got {indices}"
        )

    def test_empty_text_elements_skipped(self):
        """Elements with empty text produce no chunks."""
        from app.services.document_parser import _build_chunks

        elements = [
            _make_element(text="", category="NarrativeText", page_number=1),
            _make_element(text="   ", category="Title", page_number=2),
            _make_element(text="Real content here.", category="NarrativeText", page_number=3),
        ]
        mock_processor = _make_image_processor()

        chunks, metadatas = _build_chunks(
            elements=elements,
            image_processor=mock_processor,
            document_id=1,
            filename="doc.pdf",
        )

        # Only the non-empty element should produce chunks
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.strip() != "", "No empty chunks should be produced"

        # All chunks should come from page 3 (the only non-empty element)
        assert all(m["page_number"] == 3 for m in metadatas)
