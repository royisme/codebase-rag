#!/bin/bash

################################################################################
# API Demo Script
# Purpose: Demonstrate all core API endpoints of codebase-rag
# Usage: ./scripts/demo_curl.sh
################################################################################

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${API_BASE_URL:-http://localhost:8000}"
API_VERSION="v1"
API_BASE="${BASE_URL}/api/${API_VERSION}"

# Test data
TEST_REPO_PATH="${TEST_REPO_PATH:-/tmp/test-repo}"
TEST_REPO_ID="demo-repo-$(date +%s)"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}codebase-rag API Demo${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Base URL: ${BLUE}${BASE_URL}${NC}"
echo -e "Test Repo: ${BLUE}${TEST_REPO_PATH}${NC}"
echo ""

# Function to print API call
print_api_call() {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
    echo -e "${BLUE}$2${NC}"
}

# Function to make API call and display result
api_call() {
    local description=$1
    local method=$2
    local endpoint=$3
    local data=$4

    print_api_call "$description" "$method $endpoint"

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "$endpoint")
    else
        response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$endpoint")
    fi

    # Extract HTTP status
    http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_STATUS:/d')

    # Pretty print JSON if possible
    if command -v jq &> /dev/null; then
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    else
        echo "$body"
    fi

    # Check status
    if [ "$http_status" -ge 200 ] && [ "$http_status" -lt 300 ]; then
        echo -e "${GREEN}✓ Success (HTTP $http_status)${NC}"
    else
        echo -e "${RED}✗ Failed (HTTP $http_status)${NC}"
    fi

    # Save response for later use
    echo "$body" > /tmp/last_response.json
}

################################################################################
# 1. HEALTH CHECK
################################################################################

api_call \
    "1. Health Check" \
    "GET" \
    "${API_BASE}/health"

################################################################################
# 2. SYSTEM INFO
################################################################################

api_call \
    "2. System Information" \
    "GET" \
    "${BASE_URL}/info"

################################################################################
# 3. REPOSITORY INGESTION
################################################################################

# Create test repository if it doesn't exist
if [ ! -d "$TEST_REPO_PATH" ]; then
    echo -e "\n${YELLOW}Creating test repository at ${TEST_REPO_PATH}${NC}"
    mkdir -p "$TEST_REPO_PATH/src/auth"

    cat > "$TEST_REPO_PATH/src/auth/token.py" << 'EOF'
"""Token management module"""

def generate_token(user_id: str) -> str:
    """Generate authentication token for user"""
    return f"token_{user_id}"

def validate_token(token: str) -> bool:
    """Validate authentication token"""
    return token.startswith("token_")
EOF

    cat > "$TEST_REPO_PATH/src/auth/user.py" << 'EOF'
"""User management module"""

class User:
    def __init__(self, username: str):
        self.username = username

    def authenticate(self, password: str) -> bool:
        """Authenticate user with password"""
        return len(password) > 8
EOF

    cat > "$TEST_REPO_PATH/src/main.py" << 'EOF'
"""Main application entry point"""

from auth.token import generate_token
from auth.user import User

def main():
    user = User("admin")
    if user.authenticate("password123"):
        token = generate_token("admin")
        print(f"Logged in: {token}")

if __name__ == "__main__":
    main()
EOF

    echo -e "${GREEN}✓ Test repository created${NC}"
fi

# Ingest repository
api_call \
    "3. Ingest Repository" \
    "POST" \
    "${API_BASE}/ingest/repo" \
    "{
        \"local_path\": \"$TEST_REPO_PATH\",
        \"include_globs\": [\"**/*.py\", \"**/*.ts\", \"**/*.tsx\"],
        \"exclude_globs\": [\"**/node_modules/**\", \"**/.git/**\", \"**/__pycache__/**\"]
    }"

# Wait a moment for ingestion to complete
sleep 2

################################################################################
# 4. RELATED FILES SEARCH
################################################################################

api_call \
    "4a. Search Related Files - 'auth'" \
    "GET" \
    "${API_BASE}/graph/related?query=auth&repoId=${TEST_REPO_ID}&limit=10"

api_call \
    "4b. Search Related Files - 'token'" \
    "GET" \
    "${API_BASE}/graph/related?query=token&repoId=${TEST_REPO_ID}&limit=10"

api_call \
    "4c. Search Related Files - 'user'" \
    "GET" \
    "${API_BASE}/graph/related?query=user&repoId=${TEST_REPO_ID}&limit=10"

################################################################################
# 5. CONTEXT PACK GENERATION
################################################################################

api_call \
    "5a. Context Pack - Plan Stage" \
    "GET" \
    "${API_BASE}/context/pack?repoId=${TEST_REPO_ID}&stage=plan&budget=1500&keywords=auth,token"

api_call \
    "5b. Context Pack - Review Stage with Focus" \
    "GET" \
    "${API_BASE}/context/pack?repoId=${TEST_REPO_ID}&stage=review&budget=2000&keywords=auth&focus=src/auth"

api_call \
    "5c. Context Pack - Large Budget" \
    "GET" \
    "${API_BASE}/context/pack?repoId=${TEST_REPO_ID}&stage=implement&budget=5000"

################################################################################
# 6. IMPACT ANALYSIS
################################################################################

api_call \
    "6a. Impact Analysis - token.py (depth=1)" \
    "GET" \
    "${API_BASE}/graph/impact?repoId=${TEST_REPO_ID}&file=src/auth/token.py&depth=1&limit=50"

api_call \
    "6b. Impact Analysis - user.py (depth=2)" \
    "GET" \
    "${API_BASE}/graph/impact?repoId=${TEST_REPO_ID}&file=src/auth/user.py&depth=2&limit=50"

################################################################################
# 7. GRAPH STATISTICS
################################################################################

api_call \
    "7. Graph Statistics" \
    "GET" \
    "${API_BASE}/statistics"

################################################################################
# 8. GRAPH SCHEMA
################################################################################

api_call \
    "8. Graph Schema" \
    "GET" \
    "${API_BASE}/schema"

################################################################################
# SUMMARY
################################################################################

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Demo Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "API Endpoints Tested:"
echo -e "  ${GREEN}✓${NC} GET  /api/v1/health"
echo -e "  ${GREEN}✓${NC} GET  /info"
echo -e "  ${GREEN}✓${NC} POST /api/v1/ingest/repo"
echo -e "  ${GREEN}✓${NC} GET  /api/v1/graph/related"
echo -e "  ${GREEN}✓${NC} GET  /api/v1/context/pack"
echo -e "  ${GREEN}✓${NC} GET  /api/v1/graph/impact"
echo -e "  ${GREEN}✓${NC} GET  /api/v1/statistics"
echo -e "  ${GREEN}✓${NC} GET  /api/v1/schema"
echo ""
echo -e "For interactive API documentation, visit:"
echo -e "  ${BLUE}${BASE_URL}/docs${NC}"
echo ""
echo -e "Test repository created at:"
echo -e "  ${BLUE}${TEST_REPO_PATH}${NC}"
echo ""

# Cleanup option
read -p "Remove test repository? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$TEST_REPO_PATH"
    echo -e "${GREEN}✓ Test repository removed${NC}"
fi
