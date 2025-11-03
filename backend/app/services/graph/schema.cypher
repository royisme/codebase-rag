// Neo4j schema constraints and indexes for codebase-rag v0.2
// Run this script with: cypher-shell -u neo4j -p password < schema.cypher

// Repo constraint
CREATE CONSTRAINT repo_key IF NOT EXISTS
FOR (r:Repo) REQUIRE (r.id) IS UNIQUE;

// File constraint - composite key on repoId and path
CREATE CONSTRAINT file_key IF NOT EXISTS
FOR (f:File) REQUIRE (f.repoId, f.path) IS NODE KEY;

// Fulltext index for file search
CREATE FULLTEXT INDEX file_text IF NOT EXISTS
FOR (f:File) ON EACH [f.path, f.lang, f.content];

// Symbol constraint (v0.3+, placeholder for now)
CREATE CONSTRAINT sym_key IF NOT EXISTS
FOR (s:Symbol) REQUIRE (s.id) IS UNIQUE;

// Indexes for performance
CREATE INDEX file_repo_idx IF NOT EXISTS
FOR (f:File) ON (f.repoId);

CREATE INDEX file_lang_idx IF NOT EXISTS
FOR (f:File) ON (f.lang);
