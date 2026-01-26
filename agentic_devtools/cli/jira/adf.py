"""
Atlassian Document Format (ADF) to plain text conversion.

ADF is used in Jira Cloud and newer Jira Server versions.
"""

from typing import Any


def _convert_adf_to_text(node: Any, indent_level: int = 0) -> str:
    """
    Convert Atlassian Document Format (ADF) to plain text.

    Handles common node types: text, paragraph, heading, bulletList,
    orderedList, listItem, codeBlock, blockquote, hardBreak.

    Args:
        node: ADF node (dict, list, or string)
        indent_level: Current indentation level for nested content

    Returns:
        Plain text representation of the ADF content
    """
    if node is None:
        return ""

    if isinstance(node, str):
        return node

    if isinstance(node, dict):
        node_type = node.get("type", "")

        # Text node - return the text content
        if "text" in node:
            return str(node["text"])

        # Block-level nodes that need newlines
        if node_type == "paragraph":
            content = _process_adf_children(node, indent_level)
            return f"{content}\n" if content else ""

        if node_type == "heading":
            content = _process_adf_children(node, indent_level)
            level = node.get("attrs", {}).get("level", 1)
            prefix = "#" * level + " "
            return f"{prefix}{content}\n" if content else ""

        if node_type == "bulletList":
            items = []
            for child in node.get("content", []):
                item_text = _convert_adf_to_text(child, indent_level + 1)
                if item_text:
                    items.append(f"{'  ' * indent_level}• {item_text.strip()}")
            return "\n".join(items) + "\n" if items else ""

        if node_type == "orderedList":
            items = []
            for idx, child in enumerate(node.get("content", []), 1):
                item_text = _convert_adf_to_text(child, indent_level + 1)
                if item_text:
                    items.append(f"{'  ' * indent_level}{idx}. {item_text.strip()}")
            return "\n".join(items) + "\n" if items else ""

        if node_type == "listItem":
            return _process_adf_children(node, indent_level)

        if node_type == "codeBlock":
            content = _process_adf_children(node, indent_level)
            return f"```\n{content}\n```\n" if content else ""

        if node_type == "blockquote":
            content = _process_adf_children(node, indent_level)
            if content:
                lines = content.strip().split("\n")
                return "\n".join(f"> {line}" for line in lines) + "\n"
            return ""

        if node_type == "hardBreak":
            return "\n"

        # Default: recursively process content
        return _process_adf_children(node, indent_level)

    if isinstance(node, list):
        parts = [_convert_adf_to_text(item, indent_level) for item in node]
        return "".join(part for part in parts if part)

    return ""


def _process_adf_children(node: dict, indent_level: int = 0) -> str:
    """
    Process children of an ADF node.

    Args:
        node: ADF node dictionary
        indent_level: Current indentation level

    Returns:
        Concatenated text from all children
    """
    if "content" not in node:
        return ""
    parts = [_convert_adf_to_text(child, indent_level) for child in node["content"]]
    return "".join(part for part in parts if part)
