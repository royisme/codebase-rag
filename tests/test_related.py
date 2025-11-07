"""
Tests for related files search functionality
Tests GET /graph/related endpoint
"""
import pytest
from src.codebase_rag.services.utils import Ranker


class TestRanker:
    """Test ranking service"""

    @pytest.mark.unit
    def test_rank_files_basic(self, sample_files):
        """Test basic file ranking"""
        ranker = Ranker()

        ranked = ranker.rank_files(
            files=sample_files,
            query="auth token",
            limit=10
        )

        assert len(ranked) > 0
        assert all("score" in f for f in ranked)

        # Verify results are sorted by score
        scores = [f["score"] for f in ranked]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.unit
    def test_rank_exact_match_priority(self, sample_files):
        """Test that exact path matches get higher scores"""
        ranker = Ranker()

        ranked = ranker.rank_files(
            files=sample_files,
            query="token",
            limit=10
        )

        # File with 'token' in path should rank high
        token_file = next((f for f in ranked if "token" in f["path"]), None)
        assert token_file is not None
        assert token_file["score"] > 1.0  # Should have boosted score

    @pytest.mark.unit
    def test_generate_file_summary(self):
        """Test rule-based summary generation"""
        ranker = Ranker()

        summary = ranker.generate_file_summary(
            path="src/auth/token.py",
            lang="python"
        )

        assert "python" in summary.lower()
        assert "token.py" in summary.lower()
        assert "auth" in summary.lower()

    @pytest.mark.unit
    def test_generate_ref_handle(self):
        """Test ref:// handle generation"""
        ranker = Ranker()

        ref = ranker.generate_ref_handle(
            path="src/auth/token.py",
            start_line=1,
            end_line=100
        )

        assert ref.startswith("ref://file/")
        assert "src/auth/token.py" in ref
        assert "#L1-L100" in ref


class TestRelatedAPI:
    """Test related files API endpoint"""

    @pytest.mark.integration
    def test_related_basic(self, test_client, test_repo_id):
        """Test basic related files query"""
        response = test_client.get(
            f"/api/v1/graph/related?query=auth&repoId={test_repo_id}&limit=10"
        )

        # May return empty if no files ingested yet
        assert response.status_code == 200
        data = response.json()

        assert "nodes" in data
        assert "query" in data
        assert "repo_id" in data
        assert data["query"] == "auth"
        assert data["repo_id"] == test_repo_id

    @pytest.mark.integration
    def test_related_returns_correct_format(self, test_client, test_repo_id):
        """Test that related endpoint returns NodeSummary format"""
        response = test_client.get(
            f"/api/v1/graph/related?query=test&repoId={test_repo_id}&limit=5"
        )

        assert response.status_code == 200
        data = response.json()

        # Check each node has required fields
        for node in data["nodes"]:
            assert "type" in node
            assert "ref" in node
            assert "path" in node
            assert "score" in node
            assert "summary" in node
            assert node["ref"].startswith("ref://file/")

    @pytest.mark.integration
    def test_related_limit_parameter(self, test_client, test_repo_id):
        """Test that limit parameter is respected"""
        limit = 3

        response = test_client.get(
            f"/api/v1/graph/related?query=*&repoId={test_repo_id}&limit={limit}"
        )

        assert response.status_code == 200
        data = response.json()

        # Should return at most 'limit' results
        assert len(data["nodes"]) <= limit

    @pytest.mark.integration
    def test_related_empty_results(self, test_client):
        """Test related query with no matches"""
        response = test_client.get(
            "/api/v1/graph/related?query=nonexistentfile12345&repoId=fake-repo&limit=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 0

    @pytest.mark.integration
    def test_related_requires_params(self, test_client):
        """Test that required parameters are enforced"""
        # Missing query
        response = test_client.get("/api/v1/graph/related?repoId=test")
        assert response.status_code == 422

        # Missing repoId
        response = test_client.get("/api/v1/graph/related?query=test")
        assert response.status_code == 422


class TestRelatedPerformance:
    """Performance tests for related files search"""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_related_performance(self, test_client, test_repo_id):
        """Test that related query completes in reasonable time"""
        import time

        start = time.time()
        response = test_client.get(
            f"/api/v1/graph/related?query=test&repoId={test_repo_id}&limit=30"
        )
        duration = time.time() - start

        assert response.status_code == 200
        # Should complete in less than 1 second for small repos
        assert duration < 1.0, f"Query took {duration}s, expected < 1s"


class TestFulltextSearch:
    """Test fulltext search functionality"""

    @pytest.mark.integration
    def test_fulltext_with_data(self, test_client, test_repo_path, test_repo_id):
        """Test fulltext search after ingesting data"""
        # First ingest some data
        ingest_response = test_client.post("/api/v1/ingest/repo", json={
            "local_path": test_repo_path,
            "include_globs": ["**/*.py", "**/*.ts"],
            "exclude_globs": []
        })

        assert ingest_response.status_code == 200

        # Now search
        response = test_client.get(
            f"/api/v1/graph/related?query=helper&repoId={test_repo_id}&limit=10"
        )

        assert response.status_code == 200
        data = response.json()

        # Should find files with "helper" in name
        if len(data["nodes"]) > 0:
            helper_files = [n for n in data["nodes"] if "helper" in n["path"].lower()]
            assert len(helper_files) > 0
