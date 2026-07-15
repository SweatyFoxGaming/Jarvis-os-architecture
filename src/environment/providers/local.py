import os
import logging
import shutil
import fnmatch
from typing import Dict, Any, List, Optional

from src.environment.providers.base import EnvironmentProvider
from src.environment.models import ProviderHealth, ProviderMetadata, Domain, EnvironmentProviderCapability

logger = logging.getLogger(__name__)


class LocalFilesystemProvider(EnvironmentProvider):
    def __init__(self, secure_memory=None, allowed_paths: Optional[List[str]] = None):
        self.secure_memory = secure_memory
        self.allowed_paths = allowed_paths or []
        self.allowed_paths = [os.path.expanduser(p) for p in self.allowed_paths]
        self._health = ProviderHealth.LOADING
        self._initialized = False

    def _is_path_allowed(self, path: str) -> bool:
        if not self.allowed_paths:
            return False
        try:
            real_path = os.path.realpath(os.path.expanduser(path))
        except Exception:
            return False
        for allowed in self.allowed_paths:
            allowed_real = os.path.realpath(os.path.expanduser(allowed))
            if real_path.startswith(allowed_real + os.sep) or real_path == allowed_real:
                return True
        return False

    def initialize(self) -> None:
        self._health = ProviderHealth.AVAILABLE
        self._initialized = True
        logger.info(f"[LocalFilesystemProvider] Initialized. Allowed paths: {self.allowed_paths}")

    def shutdown(self) -> None:
        self._health = ProviderHealth.OFFLINE
        self._initialized = False
        logger.info("[LocalFilesystemProvider] Shut down.")

    def health(self) -> ProviderHealth:
        return self._health

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            name="local_fs",
            domain=Domain.FILESYSTEM,
            version="1.0.0",
            author="Jarvis Core Team",
            description="Local filesystem access with path restrictions.",
            capabilities=[
                EnvironmentProviderCapability(
                    name="list",
                    description="List directory contents",
                    parameters={"path": {"type": "string", "description": "Directory path"}},
                    returns={"files": {"type": "array", "description": "List of file/directory names"}}
                ),
                EnvironmentProviderCapability(
                    name="read",
                    description="Read file content",
                    parameters={"path": {"type": "string", "description": "File path"}},
                    returns={"content": {"type": "string", "description": "File content"}}
                ),
                EnvironmentProviderCapability(
                    name="write",
                    description="Write content to a file",
                    parameters={"path": {"type": "string"}, "content": {"type": "string"}},
                    returns={"success": {"type": "boolean"}}
                ),
                EnvironmentProviderCapability(
                    name="delete",
                    description="Delete a file or empty directory",
                    parameters={"path": {"type": "string"}},
                    returns={"success": {"type": "boolean"}}
                ),
                EnvironmentProviderCapability(
                    name="mkdir",
                    description="Create a directory",
                    parameters={"path": {"type": "string"}},
                    returns={"success": {"type": "boolean"}}
                ),
                EnvironmentProviderCapability(
                    name="copy",
                    description="Copy a file or directory",
                    parameters={"src": {"type": "string"}, "dst": {"type": "string"}},
                    returns={"success": {"type": "boolean"}}
                ),
                EnvironmentProviderCapability(
                    name="move",
                    description="Move a file or directory",
                    parameters={"src": {"type": "string"}, "dst": {"type": "string"}},
                    returns={"success": {"type": "boolean"}}
                ),
                EnvironmentProviderCapability(
                    name="metadata",
                    description="Get file/directory metadata",
                    parameters={"path": {"type": "string"}},
                    returns={"metadata": {"type": "object"}}
                ),
                EnvironmentProviderCapability(
                    name="search",
                    description="Search for files matching a pattern",
                    parameters={"path": {"type": "string"}, "pattern": {"type": "string"}, "recursive": {"type": "boolean"}},
                    returns={"results": {"type": "array"}}
                ),
            ]
        )

    def capabilities(self) -> List[str]:
        return ["list", "read", "write", "delete", "mkdir", "copy", "move", "metadata", "search"]

    def execute(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            return {"error": "Provider not initialized"}

        path = params.get('path')
        content = params.get('content')
        src = params.get('src')
        dst = params.get('dst')
        pattern = params.get('pattern')
        recursive = params.get('recursive', True)

        try:
            if capability == "list":
                if not path:
                    path = "."
                if not self._is_path_allowed(path):
                    return {"error": "Permission denied: path outside allowed directories"}
                if not os.path.exists(path):
                    return {"error": f"Path does not exist: {path}"}
                items = os.listdir(path)
                details = []
                for item in items:
                    full = os.path.join(path, item)
                    try:
                        st = os.stat(full)
                        details.append({
                            "name": item,
                            "is_dir": os.path.isdir(full),
                            "size": st.st_size,
                            "modified": st.st_mtime,
                        })
                    except:
                        details.append({"name": item, "is_dir": os.path.isdir(full)})
                return {"files": items, "details": details}

            elif capability == "read":
                if not path:
                    return {"error": "Missing 'path'"}
                if not self._is_path_allowed(path):
                    return {"error": "Permission denied: path outside allowed directories"}
                if not os.path.exists(path):
                    return {"error": f"File not found: {path}"}
                if not os.path.isfile(path):
                    return {"error": f"Path is not a file: {path}"}
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                return {"content": content}

            elif capability == "write":
                if not path:
                    return {"error": "Missing 'path'"}
                if content is None:
                    return {"error": "Missing 'content'"}
                if not self._is_path_allowed(path):
                    return {"error": "Permission denied: path outside allowed directories"}
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return {"success": True}

            elif capability == "delete":
                if not path:
                    return {"error": "Missing 'path'"}
                if not self._is_path_allowed(path):
                    return {"error": "Permission denied: path outside allowed directories"}
                if not os.path.exists(path):
                    return {"error": f"Path not found: {path}"}
                if os.path.isdir(path):
                    if os.listdir(path):
                        return {"error": "Directory not empty"}
                    os.rmdir(path)
                else:
                    os.remove(path)
                return {"success": True}

            elif capability == "mkdir":
                if not path:
                    return {"error": "Missing 'path'"}
                if not self._is_path_allowed(path):
                    return {"error": "Permission denied: path outside allowed directories"}
                os.makedirs(path, exist_ok=True)
                return {"success": True}

            elif capability == "copy":
                if not src or not dst:
                    return {"error": "Missing 'src' or 'dst'"}
                if not self._is_path_allowed(src) or not self._is_path_allowed(dst):
                    return {"error": "Permission denied: source or destination outside allowed directories"}
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
                return {"success": True}

            elif capability == "move":
                if not src or not dst:
                    return {"error": "Missing 'src' or 'dst'"}
                if not self._is_path_allowed(src) or not self._is_path_allowed(dst):
                    return {"error": "Permission denied: source or destination outside allowed directories"}
                shutil.move(src, dst)
                return {"success": True}

            elif capability == "metadata":
                if not path:
                    return {"error": "Missing 'path'"}
                if not self._is_path_allowed(path):
                    return {"error": "Permission denied: path outside allowed directories"}
                if not os.path.exists(path):
                    return {"error": f"Path not found: {path}"}
                st = os.stat(path)
                return {
                    "metadata": {
                        "size": st.st_size,
                        "modified": st.st_mtime,
                        "accessed": st.st_atime,
                        "created": st.st_ctime,
                        "is_dir": os.path.isdir(path),
                        "is_file": os.path.isfile(path),
                        "is_symlink": os.path.islink(path),
                        "permissions": oct(st.st_mode)[-3:],
                        "owner": st.st_uid,
                        "group": st.st_gid,
                    }
                }

            elif capability == "search":
                if not path or not pattern:
                    return {"error": "Missing 'path' or 'pattern'"}
                if not self._is_path_allowed(path):
                    return {"error": "Permission denied: path outside allowed directories"}
                results = []
                if recursive:
                    for root, dirs, files in os.walk(path):
                        for name in files + dirs:
                            if fnmatch.fnmatch(name, pattern):
                                results.append(os.path.join(root, name))
                else:
                    try:
                        for name in os.listdir(path):
                            if fnmatch.fnmatch(name, pattern):
                                results.append(os.path.join(path, name))
                    except:
                        pass
                return {"results": results}

            else:
                return {"error": f"Unknown capability: {capability}"}

        except PermissionError as e:
            return {"error": f"Permission denied: {str(e)}"}
        except Exception as e:
            logger.error(f"[LocalFilesystemProvider] Error executing {capability}: {e}", exc_info=True)
            return {"error": str(e)}
