"""
File tool utilities for AI assistant file operations.
"""
from pathlib import Path
from typing import Dict, Any
from utils.file_utils import _resolve_safe_path, _workspace_roots


def _tool_list_files(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    List files in a directory with optional pattern matching.
    """
    try:
        directory = params.get("directory", ".")
        pattern = params.get("pattern", "*")
        
        safe_path = _resolve_safe_path(directory)
        
        if not safe_path.is_dir():
            return {
                "status": "error",
                "message": f"Path is not a directory: {directory}"
            }
        
        files = []
        for file_path in safe_path.glob(pattern):
            if file_path.is_file():
                files.append(file_path.name)
        
        return {
            "status": "success",
            "directory": str(safe_path),
            "files": sorted(files),
            "count": len(files)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def _tool_read_file(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read contents of a file.
    """
    try:
        file_path = params.get("file_path")
        if not file_path:
            return {
                "status": "error",
                "message": "file_path parameter is required"
            }
        
        safe_path = _resolve_safe_path(file_path)
        
        if not safe_path.is_file():
            return {
                "status": "error",
                "message": f"File not found: {file_path}"
            }
        
        # Limit file size for safety
        max_size = params.get("max_size", 10000)  # 10KB default
        content = safe_path.read_text(encoding='utf-8', errors='ignore')
        
        if len(content) > max_size:
            content = content[:max_size]
            truncated = True
        else:
            truncated = False
        
        return {
            "status": "success",
            "file_path": str(safe_path),
            "content": content,
            "truncated": truncated,
            "size": len(content)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def _tool_write_file(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Write content to a file.
    """
    try:
        file_path = params.get("file_path")
        content = params.get("content", "")
        
        if not file_path:
            return {
                "status": "error",
                "message": "file_path parameter is required"
            }
        
        safe_path = _resolve_safe_path(file_path)
        
        # Create parent directories if needed
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        
        safe_path.write_text(content, encoding='utf-8')
        
        return {
            "status": "success",
            "file_path": str(safe_path),
            "size": len(content)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }