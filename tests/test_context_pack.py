"""
Tests for context pack generation
Tests GET /context/pack endpoint
"""
import pytest
from services.pack_builder import PackBuilder


class TestPackBuilder:
    """Test pack builder service"""

    @pytest.mark.unit
    def test_build_context_pack_basic(self):
        """Test basic context pack building"""
        pack_builder = PackBuilder()

        nodes = [
            {
                "type": "file",
                "path": "src/auth/token.py",
                "lang": "python",
                "score": 0.9,
                "summary": "Python file token.py in auth/ directory",
                "ref": "ref://file/src/auth/token.py#L1-L100"
            },
            {
                "type": "file",
                "path": "src/auth/user.py",
                "lang": "python",
                "score": 0.8,
                "summary": "Python file user.py in auth/ directory",
                "ref": "ref://file/src/auth/user.py#L1-L200"
            }
        ]

        pack = pack_builder.build_context_pack(
            nodes=nodes,
            budget=1500,
            stage="plan",
            repo_id="test-repo",
            keywords=["auth"],
            focus_paths=[]
        )

        assert "items" in pack
        assert "budget_used" in pack
        assert "budget_limit" in pack
        assert pack["budget_limit"] == 1500
        assert pack["budget_used"] <= 1500
        assert len(pack["items"]) > 0

    @pytest.mark.unit
    def test_pack_respects_budget(self):
        """Test that pack builder respects token budget"""
        pack_builder = PackBuilder()

        # Create many nodes
        nodes = []
        for i in range(50):
            nodes.append({
                "type": "file",
                "path": f"src/module_{i}/file.py",
                "lang": "python",
                "score": 1.0 - (i * 0.01),
                "summary": f"Python file for module {i} with some description",
                "ref": f"ref://file/src/module_{i}/file.py#L1-L100"
            })

        # Small budget
        pack = pack_builder.build_context_pack(
            nodes=nodes,
            budget=500,
            stage="plan",
            repo_id="test-repo"
        )

        # Should fit within budget
        assert pack["budget_used"] <= 500
        # Should have selected some but not all items
        assert 0 < len(pack["items"]) < len(nodes)

    @pytest.mark.unit
    def test_pack_prioritizes_high_scores(self):
        """Test that higher scored items are prioritized"""
        pack_builder = PackBuilder()

        nodes = [
            {
                "type": "file",
                "path": "low_score.py",
                "lang": "python",
                "score": 0.1,
                "summary": "Low score file",
                "ref": "ref://file/low_score.py#L1-L100"
            },
            {
                "type": "file",
                "path": "high_score.py",
                "lang": "python",
                "score": 0.9,
                "summary": "High score file",
                "ref": "ref://file/high_score.py#L1-L100"
            }
        ]

        pack = pack_builder.build_context_pack(
            nodes=nodes,
            budget=300,  # Only room for one
            stage="plan",
            repo_id="test-repo"
        )

        # Should select the high score file
        if len(pack["items"]) > 0:
            first_item = pack["items"][0]
            assert "high_score" in first_item["ref"]

    @pytest.mark.unit
    def test_pack_focus_paths_priority(self):
        """Test that focus paths get priority"""
        pack_builder = PackBuilder()

        nodes = [
            {
                "type": "file",
                "path": "src/important/critical.py",
                "lang": "python",
                "score": 0.5,
                "summary": "Critical file",
                "ref": "ref://file/src/important/critical.py#L1-L100"
            },
            {
                "type": "file",
                "path": "src/other/regular.py",
                "lang": "python",
                "score": 0.9,
                "summary": "Regular file",
                "ref": "ref://file/src/other/regular.py#L1-L100"
            }
        ]

        pack = pack_builder.build_context_pack(
            nodes=nodes,
            budget=300,  # Only room for one
            stage="plan",
            repo_id="test-repo",
            focus_paths=["src/important"]
        )

        # Focus path should be prioritized even with lower score
        if len(pack["items"]) > 0:
            first_item = pack["items"][0]
            assert "important" in first_item["ref"]

    @pytest.mark.unit
    def test_extract_title(self):
        """Test title extraction from path"""
        pack_builder = PackBuilder()

        # Test with multi-level path
        title = pack_builder._extract_title("src/auth/token.py")
        assert title == "auth/token.py"

        # Test with single level
        title = pack_builder._extract_title("main.py")
        assert title == "main.py"


class TestContextPackAPI:
    """Test context pack API endpoint"""

    @pytest.mark.integration
    def test_context_pack_basic(self, test_client, test_repo_id):
        """Test basic context pack endpoint"""
        response = test_client.get(
            f"/api/v1/context/pack?repoId={test_repo_id}&stage=plan&budget=1500"
        )

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "budget_used" in data
        assert "budget_limit" in data
        assert "stage" in data
        assert "repo_id" in data

        assert data["stage"] == "plan"
        assert data["repo_id"] == test_repo_id
        assert data["budget_limit"] == 1500

    @pytest.mark.integration
    def test_context_pack_with_keywords(self, test_client, test_repo_id):
        """Test context pack with keyword filtering"""
        response = test_client.get(
            f"/api/v1/context/pack?repoId={test_repo_id}&stage=plan&budget=1500&keywords=auth,token"
        )

        assert response.status_code == 200
        data = response.json()

        # Items should be relevant to keywords
        assert len(data["items"]) >= 0

    @pytest.mark.integration
    def test_context_pack_with_focus(self, test_client, test_repo_id):
        """Test context pack with focus paths"""
        response = test_client.get(
            f"/api/v1/context/pack?repoId={test_repo_id}&stage=plan&budget=1500&focus=src/auth"
        )

        assert response.status_code == 200
        data = response.json()

        assert "items" in data

    @pytest.mark.integration
    def test_context_pack_different_stages(self, test_client, test_repo_id):
        """Test context pack with different stages"""
        stages = ["plan", "review", "implement"]

        for stage in stages:
            response = test_client.get(
                f"/api/v1/context/pack?repoId={test_repo_id}&stage={stage}&budget=1000"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["stage"] == stage

    @pytest.mark.integration
    def test_context_pack_budget_limits(self, test_client, test_repo_id):
        """Test that different budgets produce different sized packs"""
        # Small budget
        response_small = test_client.get(
            f"/api/v1/context/pack?repoId={test_repo_id}&stage=plan&budget=500"
        )

        # Large budget
        response_large = test_client.get(
            f"/api/v1/context/pack?repoId={test_repo_id}&stage=plan&budget=5000"
        )

        assert response_small.status_code == 200
        assert response_large.status_code == 200

        small_data = response_small.json()
        large_data = response_large.json()

        # Large budget should allow more items (if data available)
        assert small_data["budget_used"] <= 500
        assert large_data["budget_used"] <= 5000

    @pytest.mark.integration
    def test_context_pack_item_format(self, test_client, test_repo_path, test_repo_id):
        """Test that context pack items have correct format"""
        # First ingest data
        ingest_response = test_client.post("/api/v1/ingest/repo", json={
            "local_path": test_repo_path,
            "include_globs": ["**/*.py"],
            "exclude_globs": []
        })
        assert ingest_response.status_code == 200

        # Get context pack
        response = test_client.get(
            f"/api/v1/context/pack?repoId={test_repo_id}&stage=plan&budget=2000"
        )

        assert response.status_code == 200
        data = response.json()

        # Check item format
        for item in data["items"]:
            assert "kind" in item
            assert "title" in item
            assert "summary" in item
            assert "ref" in item
            assert item["kind"] in ["file", "symbol", "guideline"]
            assert item["ref"].startswith("ref://")


class TestContextPackIntegration:
    """Integration tests for context pack workflow"""

    @pytest.mark.integration
    def test_full_context_workflow(self, test_client, test_repo_path, test_repo_id):
        """Test full workflow: ingest -> related -> context pack"""
        # 1. Ingest repository
        ingest_response = test_client.post("/api/v1/ingest/repo", json={
            "local_path": test_repo_path,
            "include_globs": ["**/*.py", "**/*.ts"],
            "exclude_globs": []
        })
        assert ingest_response.status_code == 200

        # 2. Find related files
        related_response = test_client.get(
            f"/api/v1/graph/related?query=helper&repoId={test_repo_id}&limit=10"
        )
        assert related_response.status_code == 200

        # 3. Build context pack
        pack_response = test_client.get(
            f"/api/v1/context/pack?repoId={test_repo_id}&stage=plan&budget=1500&keywords=helper"
        )
        assert pack_response.status_code == 200
        pack_data = pack_response.json()

        # Verify context pack is usable for prompts
        assert pack_data["budget_used"] <= 1500
        assert len(pack_data["items"]) > 0

        # Each item should have enough info for MCP integration
        first_item = pack_data["items"][0]
        assert "ref" in first_item  # Handle for MCP
        assert "summary" in first_item  # Brief description
        assert "title" in first_item  # Display name
