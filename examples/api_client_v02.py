#!/usr/bin/env python3
"""
Example client for codebase-rag v0.2 API
Demonstrates programmatic usage of the API
"""
import httpx
import json
from typing import Optional, List, Dict, Any


class CodebaseRAGClient:
    """Client for codebase-rag v0.2 API"""
    
    def __init__(self, base_url: str = "http://localhost:8123"):
        """Initialize client"""
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=300.0)
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        response = self.client.get(f"{self.base_url}/api/v1/health")
        response.raise_for_status()
        return response.json()
    
    def ingest_repo(
        self,
        local_path: Optional[str] = None,
        repo_url: Optional[str] = None,
        branch: str = "main",
        include_globs: Optional[List[str]] = None,
        exclude_globs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Ingest a repository"""
        
        if include_globs is None:
            include_globs = ["**/*.py", "**/*.ts", "**/*.tsx"]
        
        if exclude_globs is None:
            exclude_globs = [
                "**/node_modules/**",
                "**/.git/**",
                "**/__pycache__/**",
                "**/dist/**",
                "**/build/**"
            ]
        
        payload = {
            "local_path": local_path,
            "repo_url": repo_url,
            "branch": branch,
            "include_globs": include_globs,
            "exclude_globs": exclude_globs
        }
        
        response = self.client.post(
            f"{self.base_url}/api/v1/ingest/repo",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def search_related(
        self,
        repo_id: str,
        query: str,
        limit: int = 30
    ) -> Dict[str, Any]:
        """Search for related files"""
        
        params = {
            "repoId": repo_id,
            "query": query,
            "limit": limit
        }
        
        response = self.client.get(
            f"{self.base_url}/api/v1/graph/related",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_context_pack(
        self,
        repo_id: str,
        stage: str = "plan",
        budget: int = 1500,
        keywords: Optional[str] = None,
        focus: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get context pack"""
        
        params = {
            "repoId": repo_id,
            "stage": stage,
            "budget": budget
        }
        
        if keywords:
            params["keywords"] = keywords
        if focus:
            params["focus"] = focus
        
        response = self.client.get(
            f"{self.base_url}/api/v1/context/pack",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def close(self):
        """Close the client"""
        self.client.close()


def main():
    """Example usage"""
    
    print("=== Codebase RAG v0.2 Client Example ===\n")
    
    # Initialize client
    client = CodebaseRAGClient("http://localhost:8123")
    
    try:
        # 1. Health check
        print("1. Checking API health...")
        health = client.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Neo4j: {health['services']['neo4j']}")
        print()
        
        # 2. Ingest repository
        print("2. Ingesting repository...")
        repo_path = "/path/to/your/repo"  # Change this!
        
        # Uncomment to actually ingest:
        # ingest_result = client.ingest_repo(
        #     local_path=repo_path,
        #     include_globs=["**/*.py", "**/*.ts"]
        # )
        # print(f"   Task ID: {ingest_result['task_id']}")
        # print(f"   Status: {ingest_result['status']}")
        # print(f"   Files: {ingest_result.get('files_processed', 0)}")
        print("   (Skipped - set repo_path and uncomment)")
        print()
        
        # 3. Search for related files
        print("3. Searching for related files...")
        repo_id = "my-repo"  # Use your repo ID
        
        # Uncomment to actually search:
        # search_result = client.search_related(
        #     repo_id=repo_id,
        #     query="authentication login",
        #     limit=5
        # )
        # print(f"   Found {len(search_result['nodes'])} files")
        # for node in search_result['nodes'][:3]:
        #     print(f"   - {node['path']} (score: {node['score']:.2f})")
        #     print(f"     ref: {node['ref']}")
        print("   (Skipped - set repo_id and uncomment)")
        print()
        
        # 4. Get context pack
        print("4. Building context pack...")
        
        # Uncomment to actually get context:
        # context = client.get_context_pack(
        #     repo_id=repo_id,
        #     stage="plan",
        #     budget=1500,
        #     keywords="auth,login,user"
        # )
        # print(f"   Items: {len(context['items'])}")
        # print(f"   Budget: {context['budget_used']}/{context['budget_limit']}")
        # for item in context['items'][:3]:
        #     print(f"   - {item['title']}")
        #     print(f"     {item['summary']}")
        #     print(f"     {item['ref']}")
        print("   (Skipped - set repo_id and uncomment)")
        print()
        
        print("=== Example Complete ===")
        print("\nTo use this client:")
        print("1. Start the server: python start_v02.py")
        print("2. Update repo_path and repo_id in this script")
        print("3. Uncomment the API calls")
        print("4. Run: python examples/api_client_v02.py")
        
    finally:
        client.close()


if __name__ == "__main__":
    main()
