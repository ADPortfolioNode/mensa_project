"""
File system utilities for path resolution and file operations.
"""
import os
from pathlib import Path
from typing import Optional


def _workspace_roots() -> list[Path]:
    """
    Return sorted workspace root candidates where game files may be found.
    These are searched in order when resolving relative paths.
    """
    roots = []
    
    # Container-mounted data directory
    data_dir = os.environ.get('DATA_DIR', '/data')
    if data_dir:
        roots.append(Path(data_dir))
    
    # Current working directory (for local development)
    roots.append(Path.cwd())
    
    return sorted(set(roots))


def _map_container_style_path(path_obj: Path, workspace_root: Path) -> Path:
    """
    Map a container-style absolute path (e.g., /data/models/game_model.h5)
    to the corresponding path relative to a workspace root for validation.
    """
    try:
        return path_obj.relative_to(workspace_root)
    except ValueError:
        # path_obj is not under workspace_root, return as-is for validation
        return path_obj


def _resolve_safe_path(raw_path: str) -> Path:
    """
    Resolve a potentially container-style path to an absolute path
    within workspace bounds. Raises ValueError if path escapes workspace.
    """
    requested = Path(raw_path).expanduser().resolve()
    
    for root in _workspace_roots():
        try:
            relative = requested.relative_to(root)
            return root / relative
        except ValueError:
            continue
    
    # If no workspace root contains the path, reject it
    raise ValueError(f"Path '{raw_path}' escapes workspace bounds")