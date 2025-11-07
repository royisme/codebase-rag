"""
Tests for repository ingestion functionality
Tests POST /ingest/repo endpoint
"""
import pytest
from src.codebase_rag.services.code import CodeIngestor
from src.codebase_rag.services.graph import Neo4jGraphService


class TestCodeIngestor:
    """Test code ingestor service"""

    @pytest.mark.unit
    def test_scan_files(self, test_repo_path):
        """Test file scanning with glob patterns"""
        service = Neo4jGraphService()
        ingestor = CodeIngestor(service)

        files = ingestor.scan_files(
            repo_path=test_repo_path,
            include_globs=["**/*.py", "**/*.ts"],
            exclude_globs=["**/node_modules/**", "**/.git/**"]
        )

        assert len(files) > 0, "Should find at least one file"

        # Check file structure
        for file in files:
            assert "path" in file
            assert "lang" in file
            assert "size" in file
            assert file["lang"] in ["python", "typescript", "unknown"]

    @pytest.mark.unit
    def test_language_detection(self, test_repo_path):
        """Test language detection from file extensions"""
        service = Neo4jGraphService()
        ingestor = CodeIngestor(service)

        files = ingestor.scan_files(
            repo_path=test_repo_path,
            include_globs=["**/*.py"],
            exclude_globs=[]
        )

        python_files = [f for f in files if f["lang"] == "python"]
        assert len(python_files) > 0, "Should detect Python files"

    @pytest.mark.unit
    def test_exclude_patterns(self, test_repo_path, tmp_path):
        """Test that exclude patterns work correctly"""
        # Create a node_modules directory that should be excluded
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "package.py").write_text("# Should be excluded")

        service = Neo4jGraphService()
        ingestor = CodeIngestor(service)

        files = ingestor.scan_files(
            repo_path=str(tmp_path),
            include_globs=["**/*.py"],
            exclude_globs=["**/node_modules/**"]
        )

        # Verify no files from node_modules are included
        node_modules_files = [f for f in files if "node_modules" in f["path"]]
        assert len(node_modules_files) == 0, "Should exclude node_modules"


class TestIngestAPI:
    """Test ingestion API endpoints"""

    @pytest.mark.integration
    def test_ingest_local_repo(self, test_client, test_repo_path, test_repo_id):
        """Test ingesting a local repository"""
        response = test_client.post("/api/v1/ingest/repo", json={
            "local_path": test_repo_path,
            "include_globs": ["**/*.py", "**/*.ts"],
            "exclude_globs": ["**/node_modules/**"]
        })

        assert response.status_code == 200
        data = response.json()

        assert "task_id" in data
        assert "status" in data
        assert data["status"] in ["done", "queued", "running"]

    @pytest.mark.integration
    def test_ingest_requires_path_or_url(self, test_client):
        """Test that ingestion requires either local_path or repo_url"""
        response = test_client.post("/api/v1/ingest/repo", json={
            "include_globs": ["**/*.py"]
        })

        assert response.status_code == 400

    @pytest.mark.integration
    def test_ingest_idempotent(self, test_client, test_repo_path):
        """Test that repeated ingestion doesn't fail (upsert behavior)"""
        request_data = {
            "local_path": test_repo_path,
            "include_globs": ["**/*.py"]
        }

        # First ingestion
        response1 = test_client.post("/api/v1/ingest/repo", json=request_data)
        assert response1.status_code == 200

        # Second ingestion (should not fail)
        response2 = test_client.post("/api/v1/ingest/repo", json=request_data)
        assert response2.status_code == 200

    @pytest.mark.unit
    def test_ingest_empty_repo(self, test_client, tmp_path):
        """Test ingesting an empty directory"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        response = test_client.post("/api/v1/ingest/repo", json={
            "local_path": str(empty_dir),
            "include_globs": ["**/*.py"]
        })

        assert response.status_code == 200
        data = response.json()
        assert data.get("files_processed", 0) == 0


class TestIngestIntegration:
    """Integration tests for full ingestion flow"""

    @pytest.mark.integration
    def test_full_ingest_workflow(
        self,
        test_client,
        test_repo_path,
        test_repo_id,
        graph_service
    ):
        """Test complete workflow: ingest -> verify in Neo4j"""
        # Ingest repository
        response = test_client.post("/api/v1/ingest/repo", json={
            "local_path": test_repo_path,
            "include_globs": ["**/*.py", "**/*.ts"],
            "exclude_globs": []
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"
        assert data.get("files_processed", 0) > 0

        # Verify files were created in Neo4j
        import asyncio
        query = """
        MATCH (f:File)
        RETURN count(f) as file_count
        """
        result = asyncio.run(graph_service.execute_cypher(query))
        assert len(result.raw_result) > 0
        file_count = result.raw_result[0].get("file_count", 0)
        assert file_count > 0, "Files should be created in Neo4j"
