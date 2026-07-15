"""
Environment Platform – Local GitHub provider.
"""

import os
import logging
from typing import Dict, Any, List, Optional

try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

from src.environment.providers.base import EnvironmentProvider
from src.environment.models import ProviderHealth, ProviderMetadata, Domain, EnvironmentProviderCapability

logger = logging.getLogger(__name__)


class LocalGitHubProvider(EnvironmentProvider):
    """
    Local GitHub provider using PyGithub.
    """

    def __init__(self, secure_memory=None):
        self.secure_memory = secure_memory
        self._health = ProviderHealth.LOADING
        self._initialized = False

    def initialize(self) -> None:
        self._health = ProviderHealth.AVAILABLE
        self._initialized = True
        logger.info("[LocalGitHubProvider] Initialized.")

    def shutdown(self) -> None:
        self._health = ProviderHealth.OFFLINE
        self._initialized = False
        logger.info("[LocalGitHubProvider] Shut down.")

    def health(self) -> ProviderHealth:
        return self._health

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            name="local_github",
            domain=Domain.SERVICES,
            version="1.0.0",
            author="Jarvis Core Team",
            description="Local GitHub provider using PyGithub.",
            capabilities=[
                EnvironmentProviderCapability(
                    name="list_repos",
                    description="List repositories for the authenticated user",
                    parameters={},
                    returns={"repos": {"type": "array"}}
                ),
                EnvironmentProviderCapability(
                    name="create_repo",
                    description="Create a new repository",
                    parameters={"name": {"type": "string"}, "description": {"type": "string"}, "private": {"type": "boolean"}},
                    returns={"repo": {"type": "object"}}
                ),
                EnvironmentProviderCapability(
                    name="get_file",
                    description="Get content of a file from a repository",
                    parameters={"repo": {"type": "string"}, "path": {"type": "string"}},
                    returns={"content": {"type": "string"}}
                ),
                EnvironmentProviderCapability(
                    name="create_issue",
                    description="Create an issue in a repository",
                    parameters={"repo": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}},
                    returns={"issue": {"type": "object"}}
                ),
                EnvironmentProviderCapability(
                    name="push",
                    description="Push files to a repository",
                    parameters={"repo": {"type": "string"}, "branch": {"type": "string"}, "message": {"type": "string"}, "files": {"type": "object"}},
                    returns={"success": {"type": "boolean"}, "commit": {"type": "string"}}
                ),
            ]
        )

    def capabilities(self) -> List[str]:
        return ["list_repos", "create_repo", "get_file", "create_issue", "push"]

    def execute(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            return {"error": "Provider not initialized"}
        if not GITHUB_AVAILABLE:
            return {"error": "PyGithub not installed. Please install: pip install PyGithub"}

        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            return {"error": "GITHUB_TOKEN not set in environment variables"}

        try:
            g = Github(github_token)
            if capability == "list_repos":
                repos = []
                for repo in g.get_user().get_repos():
                    repos.append({"name": repo.name, "url": repo.html_url})
                return {"repos": repos}

            elif capability == "create_repo":
                name = params.get('name')
                if not name:
                    return {"error": "Missing 'name'"}
                description = params.get('description', "")
                private = params.get('private', False)
                repo = g.get_user().create_repo(name, description=description, private=private)
                return {"repo": {"name": repo.name, "url": repo.html_url}}

            elif capability == "get_file":
                repo_name = params.get('repo') or params.get('repository')
                path = params.get('path')
                if not repo_name or not path:
                    return {"error": "Missing 'repo' or 'path'"}
                repo = g.get_repo(repo_name)
                try:
                    contents = repo.get_contents(path)
                    return {"content": contents.decoded_content.decode()}
                except GithubException as e:
                    if e.status == 404:
                        return {"error": "File not found"}
                    return {"error": str(e)}

            elif capability == "create_issue":
                repo_name = params.get('repo') or params.get('repository')
                title = params.get('title')
                body = params.get('body', "")
                if not repo_name or not title:
                    return {"error": "Missing 'repo' or 'title'"}
                repo = g.get_repo(repo_name)
                issue = repo.create_issue(title=title, body=body)
                return {"issue": {"number": issue.number, "url": issue.html_url}}

            elif capability == "push":
                repo_name = params.get('repo') or params.get('repository')
                branch = params.get('branch', "main")
                commit_message = params.get('message', "Automated commit via Jarvis")
                files = params.get('files', {})
                if not repo_name:
                    return {"error": "Missing 'repo'"}
                if not files:
                    return {"error": "No files to push"}
                repo = g.get_repo(repo_name)
                ref = repo.get_git_ref(f"heads/{branch}")
                latest_commit = repo.get_commit(ref.object.sha)
                base_tree = latest_commit.commit.tree

                changes = []
                for file_path, content in files.items():
                    blob = repo.create_git_blob(content, "utf-8")
                    changes.append({
                        "path": file_path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": blob.sha,
                    })
                tree = repo.create_git_tree(changes, base_tree=base_tree)
                parent = repo.get_git_commit(ref.object.sha)
                commit = repo.create_git_commit(commit_message, tree, [parent])
                ref.edit(commit.sha, force=True)
                return {"success": True, "commit": commit.sha, "message": commit_message}

            else:
                return {"error": f"Unknown capability: {capability}"}

        except Exception as e:
            logger.error(f"[LocalGitHubProvider] Error executing {capability}: {e}", exc_info=True)
            return {"error": str(e)}
