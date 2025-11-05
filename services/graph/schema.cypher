// Neo4j Schema for Code Graph Knowledge System
// Version: v0.2
// This schema defines constraints and indexes for the code knowledge graph

// ============================================================================
// CONSTRAINTS (Uniqueness & Node Keys)
// ============================================================================

// Repo: Repository root node
// Each repository is uniquely identified by its ID
CREATE CONSTRAINT repo_key IF NOT EXISTS
FOR (r:Repo) REQUIRE (r.id) IS UNIQUE;

// File: Source code files
// Files are uniquely identified by the combination of repoId and path
// This allows multiple repos to have files with the same path
CREATE CONSTRAINT file_key IF NOT EXISTS
FOR (f:File) REQUIRE (f.repoId, f.path) IS NODE KEY;

// Symbol: Code symbols (functions, classes, variables, etc.)
// Each symbol has a globally unique ID
CREATE CONSTRAINT sym_key IF NOT EXISTS
FOR (s:Symbol) REQUIRE (s.id) IS UNIQUE;

// Function: Function definitions (inherits from Symbol)
CREATE CONSTRAINT function_id IF NOT EXISTS
FOR (n:Function) REQUIRE n.id IS UNIQUE;

// Class: Class definitions (inherits from Symbol)
CREATE CONSTRAINT class_id IF NOT EXISTS
FOR (n:Class) REQUIRE n.id IS UNIQUE;

// CodeEntity: Generic code entities
CREATE CONSTRAINT code_entity_id IF NOT EXISTS
FOR (n:CodeEntity) REQUIRE n.id IS UNIQUE;

// Table: Database table definitions (for SQL parsing)
CREATE CONSTRAINT table_id IF NOT EXISTS
FOR (n:Table) REQUIRE n.id IS UNIQUE;

// ============================================================================
// INDEXES (Performance Optimization)
// ============================================================================

// Fulltext Index: File search by path, language, and content
// This is the PRIMARY search index for file discovery
// Supports fuzzy matching and relevance scoring
CREATE FULLTEXT INDEX file_text IF NOT EXISTS
FOR (f:File) ON EACH [f.path, f.lang];

// Note: If you want to include content in fulltext search (can be large),
// uncomment the line below and comment out the one above:
// CREATE FULLTEXT INDEX file_text IF NOT EXISTS
// FOR (f:File) ON EACH [f.path, f.lang, f.content];

// Regular indexes for exact lookups
CREATE INDEX file_path IF NOT EXISTS
FOR (f:File) ON (f.path);

CREATE INDEX file_repo IF NOT EXISTS
FOR (f:File) ON (f.repoId);

CREATE INDEX symbol_name IF NOT EXISTS
FOR (s:Symbol) ON (s.name);

CREATE INDEX function_name IF NOT EXISTS
FOR (n:Function) ON (n.name);

CREATE INDEX class_name IF NOT EXISTS
FOR (n:Class) ON (n.name);

CREATE INDEX code_entity_name IF NOT EXISTS
FOR (n:CodeEntity) ON (n.name);

CREATE INDEX table_name IF NOT EXISTS
FOR (n:Table) ON (n.name);

// ============================================================================
// RELATIONSHIP TYPES (Documentation)
// ============================================================================

// The following relationships are created by the application:
//
// (:File)-[:IN_REPO]->(:Repo)
//   - Links files to their parent repository
//
// (:Symbol)-[:DEFINED_IN]->(:File)
//   - Links symbols (functions, classes) to the file where they are defined
//
// (:Symbol)-[:BELONGS_TO]->(:Symbol)
//   - Links class methods to their parent class
//
// (:Symbol)-[:CALLS]->(:Symbol)
//   - Function/method call relationships
//
// (:Symbol)-[:INHERITS]->(:Symbol)
//   - Class inheritance relationships
//
// (:File)-[:IMPORTS]->(:File)
//   - File import/dependency relationships
//
// (:File)-[:USES]->(:Symbol)
//   - Files that use specific symbols (implicit dependency)

// ============================================================================
// USAGE NOTES
// ============================================================================

// 1. Run this script using neo4j_bootstrap.sh or manually:
//    cat schema.cypher | cypher-shell -u neo4j -p password
//
// 2. All constraints and indexes use IF NOT EXISTS, making this script idempotent
//
// 3. To verify the schema:
//    SHOW CONSTRAINTS;
//    SHOW INDEXES;
//
// 4. To drop all constraints and indexes (use with caution):
//    DROP CONSTRAINT constraint_name IF EXISTS;
//    DROP INDEX index_name IF EXISTS;
