"""
Chat tool utilities for AI assistant functionality.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json


def _parse_datetime(value: Any) -> Optional[datetime]:
    """
    Parse various datetime formats into datetime objects.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except (ValueError, OSError):
            pass
    return None


def _extract_metadata_value(metadata: dict, preferred_tokens: list[str]) -> Optional[str]:
    """
    Extract a value from metadata preferring specific tokens.
    """
    for token in preferred_tokens:
        if token in metadata:
            return metadata[token]
    return None


def _render_tool_response(tool_name: str, tool_result: Dict[str, Any]) -> str:
    """
    Format a tool result into a human-readable response.
    """
    if tool_result.get("status") == "error":
        return f"Tool '{tool_name}' failed: {tool_result.get('message', 'Unknown error')}"
    
    # Format successful responses based on tool type
    if tool_name == "list_files":
        files = tool_result.get("files", [])
        return f"Found {len(files)} files: {', '.join(files[:10])}" + ("..." if len(files) > 10 else "")
    elif tool_name == "read_file":
        content = tool_result.get("content", "")
        preview = content[:200] + "..." if len(content) > 200 else content
        return f"File content preview: {preview}"
    elif tool_name == "internet_search":
        results = tool_result.get("results", [])
        return f"Found {len(results)} search results"
    else:
        return f"Tool '{tool_name}' completed successfully"