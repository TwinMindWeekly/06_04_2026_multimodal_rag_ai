import os

REQUIREMENTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "requirements.txt"
)


def test_requirements_utf8():
    with open(REQUIREMENTS_PATH, encoding="utf-8") as f:
        content = f.read()
    assert len(content) > 0, "requirements.txt is empty"


def test_requirements_no_null_bytes():
    with open(REQUIREMENTS_PATH, "rb") as f:
        raw = f.read()
    assert b"\x00" not in raw, "requirements.txt contains null bytes (still UTF-16?)"


def test_requirements_no_bom():
    with open(REQUIREMENTS_PATH, "rb") as f:
        first_bytes = f.read(3)
    assert first_bytes != b"\xef\xbb\xbf", "requirements.txt has UTF-8 BOM"
    assert first_bytes[:2] != b"\xff\xfe", "requirements.txt has UTF-16 LE BOM"
