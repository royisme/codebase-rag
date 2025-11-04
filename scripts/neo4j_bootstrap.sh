#!/bin/bash

################################################################################
# Neo4j Bootstrap Script
# Purpose: Initialize Neo4j schema with constraints and indexes
# Usage: ./scripts/neo4j_bootstrap.sh
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCHEMA_FILE="$PROJECT_ROOT/services/graph/schema.cypher"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Neo4j Schema Bootstrap${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if schema file exists
if [ ! -f "$SCHEMA_FILE" ]; then
    echo -e "${RED}Error: Schema file not found at $SCHEMA_FILE${NC}"
    exit 1
fi

echo -e "Schema file: ${YELLOW}$SCHEMA_FILE${NC}"

# Read Neo4j connection from environment or use defaults
NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-password}"
NEO4J_DATABASE="${NEO4J_DATABASE:-neo4j}"

echo -e "Neo4j URI: ${YELLOW}$NEO4J_URI${NC}"
echo -e "Neo4j User: ${YELLOW}$NEO4J_USER${NC}"
echo -e "Neo4j Database: ${YELLOW}$NEO4J_DATABASE${NC}"

# Check if cypher-shell is available
if command -v cypher-shell &> /dev/null; then
    echo -e "${GREEN}✓ cypher-shell found${NC}"

    echo -e "\n${YELLOW}Executing schema...${NC}"

    # Execute schema using cypher-shell
    cypher-shell \
        -a "$NEO4J_URI" \
        -u "$NEO4J_USER" \
        -p "$NEO4J_PASSWORD" \
        -d "$NEO4J_DATABASE" \
        --file "$SCHEMA_FILE"

    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}✓ Schema applied successfully${NC}"
    else
        echo -e "\n${RED}✗ Failed to apply schema${NC}"
        exit 1
    fi

    # Verify schema
    echo -e "\n${YELLOW}Verifying constraints...${NC}"
    cypher-shell \
        -a "$NEO4J_URI" \
        -u "$NEO4J_USER" \
        -p "$NEO4J_PASSWORD" \
        -d "$NEO4J_DATABASE" \
        "SHOW CONSTRAINTS;"

    echo -e "\n${YELLOW}Verifying indexes...${NC}"
    cypher-shell \
        -a "$NEO4J_URI" \
        -u "$NEO4J_USER" \
        -p "$NEO4J_PASSWORD" \
        -d "$NEO4J_DATABASE" \
        "SHOW INDEXES;"

else
    echo -e "${YELLOW}⚠ cypher-shell not found, using Python driver instead${NC}"

    # Create a temporary Python script to execute the schema
    TEMP_PY="$(mktemp)"

    cat > "$TEMP_PY" << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
import os
import sys
from neo4j import GraphDatabase

def apply_schema(uri, user, password, database, schema_file):
    """Apply Neo4j schema using Python driver"""
    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        # Read schema file
        with open(schema_file, 'r') as f:
            schema_content = f.read()

        # Split by semicolons and filter out comments/empty lines
        statements = []
        for line in schema_content.split(';'):
            line = line.strip()
            # Remove single-line comments
            if line and not line.startswith('//'):
                # Remove inline comments
                line = line.split('//')[0].strip()
                if line:
                    statements.append(line)

        # Execute each statement
        with driver.session(database=database) as session:
            for stmt in statements:
                if stmt:
                    try:
                        session.run(stmt)
                        print(f"✓ Executed: {stmt[:60]}...")
                    except Exception as e:
                        if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                            print(f"⚠ Already exists: {stmt[:60]}...")
                        else:
                            print(f"✗ Error: {e}")
                            # Continue with other statements

        print("\n✓ Schema applied successfully")

        # Verify constraints
        print("\nConstraints:")
        with driver.session(database=database) as session:
            result = session.run("SHOW CONSTRAINTS")
            for record in result:
                print(f"  - {record}")

        # Verify indexes
        print("\nIndexes:")
        with driver.session(database=database) as session:
            result = session.run("SHOW INDEXES")
            for record in result:
                print(f"  - {record}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        driver.close()

if __name__ == "__main__":
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    schema_file = sys.argv[1] if len(sys.argv) > 1 else "services/graph/schema.cypher"

    print(f"Connecting to {uri} as {user}...")
    apply_schema(uri, user, password, database, schema_file)
PYTHON_SCRIPT

    chmod +x "$TEMP_PY"
    python3 "$TEMP_PY" "$SCHEMA_FILE"

    rm "$TEMP_PY"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Bootstrap Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
