"""Tests for remove_image_references()."""

from agentic_devtools.context_budget import remove_image_references


class TestRemoveImageReferences:
    """Verify image reference removal from various formats."""

    def test_empty_string(self):
        assert remove_image_references("") == ""

    def test_no_images(self):
        text = "Just plain text with no images."
        assert remove_image_references(text) == text

    def test_removes_markdown_images(self):
        text = "Before ![alt text](https://example.com/img.png) after"
        result = remove_image_references(text)
        assert "![" not in result
        assert "Before" in result
        assert "after" in result

    def test_removes_html_img_tags(self):
        text = 'Before <img src="image.png" alt="photo"> after'
        result = remove_image_references(text)
        assert "<img" not in result
        assert "Before" in result
        assert "after" in result

    def test_removes_html_img_self_closing(self):
        text = 'Before <IMG src="image.png" /> after'
        result = remove_image_references(text)
        assert "<IMG" not in result.upper()

    def test_removes_jira_image_syntax(self):
        text = "Before !screenshot.png! after"
        result = remove_image_references(text)
        assert "!screenshot.png!" not in result
        assert "Before" in result
        assert "after" in result

    def test_removes_base64_data_uris(self):
        text = "Before data:image/png;base64,iVBORw0KGgoAAAANSUhEUg== after"
        result = remove_image_references(text)
        assert "data:image" not in result
        assert "Before" in result
        assert "after" in result

    def test_preserves_non_image_content(self):
        text = "# Title\nSome text\n- bullet point\n\nMore content"
        assert remove_image_references(text) == text
