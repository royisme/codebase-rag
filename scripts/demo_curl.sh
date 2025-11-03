#!/bin/bash
# Demo curl commands for codebase-rag v0.2 API
# Usage: ./demo_curl.sh

set -e

API_URL="${API_URL:-http://localhost:8123}"
REPO_PATH="${REPO_PATH:-/path/to/your/repo}"
REPO_ID="${REPO_ID:-my-repo}"

echo "=== Codebase RAG v0.2 Demo ==="
echo "API URL: $API_URL"
echo ""

# Health check
echo "1. Health Check"
echo "==============="
curl -s "$API_URL/api/v1/health" | python3 -m json.tool
echo ""
echo ""

# Ingest repository
echo "2. Ingest Repository"
echo "===================="
echo "Request:"
cat <<EOF
{
  "local_path": "$REPO_PATH",
  "include_globs": ["**/*.py", "**/*.ts", "**/*.tsx"],
  "exclude_globs": ["**/node_modules/**", "**/.git/**", "**/__pycache__/**"]
}
EOF
echo ""
echo "Response:"
curl -s -X POST "$API_URL/api/v1/ingest/repo" \
  -H "Content-Type: application/json" \
  -d "{
    \"local_path\": \"$REPO_PATH\",
    \"include_globs\": [\"**/*.py\", \"**/*.ts\", \"**/*.tsx\"],
    \"exclude_globs\": [\"**/node_modules/**\", \"**/.git/**\", \"**/__pycache__/**\"]
  }" | python3 -m json.tool
echo ""
echo ""

# Search related files
echo "3. Related Files Search"
echo "======================="
QUERY="auth token"
echo "Query: $QUERY"
echo "Response:"
curl -s "$API_URL/api/v1/graph/related?repoId=$REPO_ID&query=$QUERY&limit=5" \
  | python3 -m json.tool
echo ""
echo ""

# Get context pack
echo "4. Context Pack"
echo "==============="
echo "Stage: plan"
echo "Budget: 1500 tokens"
echo "Keywords: auth,token"
echo "Response:"
curl -s "$API_URL/api/v1/context/pack?repoId=$REPO_ID&stage=plan&budget=1500&keywords=auth,token" \
  | python3 -m json.tool
echo ""
echo ""

echo "=== Demo Complete ==="
echo ""
echo "Example ref:// handles:"
echo "  ref://file/src/auth/token.py#L1-L200"
echo "  ref://file/src/services/auth.ts#L1-L300"
echo ""
echo "These handles can be used with MCP tools to fetch actual code content."
