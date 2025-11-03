#!/bin/bash
# Neo4j schema bootstrap script for codebase-rag v0.2
# This script initializes the Neo4j schema with constraints and indexes

set -e

# Configuration
NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-password}"
NEO4J_DATABASE="${NEO4J_DATABASE:-neo4j}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA_FILE="$SCRIPT_DIR/../backend/app/services/graph/schema.cypher"

echo "=== Neo4j Schema Bootstrap ==="
echo "URI: $NEO4J_URI"
echo "Database: $NEO4J_DATABASE"
echo "Schema file: $SCHEMA_FILE"
echo ""

# Check if cypher-shell is available
if ! command -v cypher-shell &> /dev/null; then
    echo "Error: cypher-shell not found. Please install Neo4j client tools."
    echo ""
    echo "Alternatively, you can run the schema manually:"
    echo "  cat $SCHEMA_FILE"
    exit 1
fi

# Check if schema file exists
if [ ! -f "$SCHEMA_FILE" ]; then
    echo "Error: Schema file not found at $SCHEMA_FILE"
    exit 1
fi

# Execute schema
echo "Executing schema..."
cat "$SCHEMA_FILE" | cypher-shell \
    -a "$NEO4J_URI" \
    -u "$NEO4J_USER" \
    -p "$NEO4J_PASSWORD" \
    -d "$NEO4J_DATABASE" \
    --format plain

echo ""
echo "=== Schema initialized successfully ==="
echo ""
echo "Verify with:"
echo "  SHOW CONSTRAINTS"
echo "  SHOW INDEXES"
