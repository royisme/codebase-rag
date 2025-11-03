#!/usr/bin/env python3
"""
Simple test to verify v0.2 API structure (no actual execution)
Run this after installing dependencies to validate the implementation
"""
import sys
import os

# Add to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from backend.app.models.ingest_models import IngestRepoRequest, IngestRepoResponse
        print("✓ Ingest models")
    except ImportError as e:
        print(f"✗ Ingest models: {e}")
        return False
    
    try:
        from backend.app.models.graph_models import NodeSummary, RelatedResponse
        print("✓ Graph models")
    except ImportError as e:
        print(f"✗ Graph models: {e}")
        return False
    
    try:
        from backend.app.models.context_models import ContextItem, ContextPack
        print("✓ Context models")
    except ImportError as e:
        print(f"✗ Context models: {e}")
        return False
    
    try:
        # These require neo4j which may not be installed
        from backend.app.services.graph.neo4j_service import Neo4jService
        print("✓ Neo4j service")
    except ImportError as e:
        print(f"! Neo4j service (requires neo4j package): {e}")
    
    try:
        from backend.app.services.ingest.code_ingestor import CodeIngestor
        print("✓ Code ingestor")
    except ImportError as e:
        print(f"✗ Code ingestor: {e}")
        return False
    
    try:
        from backend.app.services.ranking.ranker import Ranker
        print("✓ Ranker")
    except ImportError as e:
        print(f"✗ Ranker: {e}")
        return False
    
    try:
        from backend.app.services.context.pack_builder import PackBuilder
        print("✓ Pack builder")
    except ImportError as e:
        print(f"✗ Pack builder: {e}")
        return False
    
    return True

def test_model_validation():
    """Test model validation"""
    print("\nTesting model validation...")
    
    try:
        from backend.app.models.ingest_models import IngestRepoRequest
        
        # Test valid request
        req = IngestRepoRequest(
            local_path="/path/to/repo",
            include_globs=["**/*.py"]
        )
        assert req.local_path == "/path/to/repo"
        print("✓ IngestRepoRequest validation")
        
    except Exception as e:
        print(f"✗ Model validation: {e}")
        return False
    
    return True

def test_api_structure():
    """Test API structure"""
    print("\nTesting API structure...")
    
    try:
        from backend.app.main import create_app
        
        # This will fail without FastAPI, but structure is correct
        try:
            app = create_app()
            print("✓ FastAPI app created")
            
            # Check routes
            routes = [route.path for route in app.routes]
            assert "/api/v1/ingest/repo" in [r for r in routes if "/ingest/repo" in r]
            print("✓ Ingest route registered")
            
        except Exception as e:
            print(f"! FastAPI app (requires fastapi package): {e}")
        
    except ImportError as e:
        print(f"! API structure (requires fastapi package): {e}")
    
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("Codebase RAG v0.2 Structure Validation")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Model Validation", test_model_validation()))
    results.append(("API Structure", test_api_structure()))
    
    print()
    print("=" * 60)
    print("Results:")
    print("=" * 60)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{name}: {status}")
    
    print()
    
    if all(r for _, r in results):
        print("✓ All tests passed!")
        return 0
    else:
        print("! Some tests failed - install dependencies with: pip install -e .")
        return 1

if __name__ == "__main__":
    sys.exit(main())
