"""
Memory Extractor - Automatic Memory Extraction (v0.7)

This module provides automatic extraction of project memories from:
- Git commits and diffs
- Code comments and documentation
- Conversations and interactions
- Knowledge base queries

Uses LLM analysis to identify and extract important project knowledge.
"""

import ast
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from llama_index.core import Settings
from loguru import logger

from services.memory_store import memory_store


class MemoryExtractor:
    """
    Extract and automatically persist project memories from various sources.

    Features:
    - LLM-based extraction from conversations
    - Git commit analysis for decisions and experiences
    - Code comment mining for conventions and plans
    - Auto-suggest memories from knowledge queries
    """

    # Processing limits
    MAX_COMMITS_TO_PROCESS = 20  # Maximum commits to analyze in batch processing
    MAX_FILES_TO_SAMPLE = 30  # Maximum files to scan for comments
    MAX_ITEMS_PER_TYPE = 3  # Top items per memory type to include
    MAX_README_LINES = 20  # Maximum README lines to process for overview
    MAX_STRING_EXCERPT_LENGTH = 200  # Maximum length for string excerpts in responses
    MAX_CONTENT_LENGTH = 500  # Maximum length for content fields
    MAX_TITLE_LENGTH = 100  # Maximum length for title fields

    def __init__(self):
        self.extraction_enabled = True
        self.confidence_threshold = 0.7  # Threshold for auto-saving
        logger.info("Memory Extractor initialized (v0.7 - full implementation)")

    async def extract_from_conversation(
        self,
        project_id: str,
        conversation: List[Dict[str, str]],
        auto_save: bool = False
    ) -> Dict[str, Any]:
        """
        Extract memories from a conversation between user and AI using LLM analysis.

        Analyzes conversation for:
        - Design decisions and rationale
        - Problems encountered and solutions
        - Preferences and conventions mentioned
        - Important architectural choices

        Args:
            project_id: Project identifier
            conversation: List of messages [{"role": "user/assistant", "content": "..."}]
            auto_save: If True, automatically save high-confidence memories (>= threshold)

        Returns:
            Dict with extracted memories and confidence scores
        """
        try:
            logger.info(f"Extracting memories from conversation ({len(conversation)} messages)")

            # Format conversation for LLM analysis
            conversation_text = self._format_conversation(conversation)

            # Create extraction prompt
            extraction_prompt = f"""Analyze the following conversation between a user and an AI assistant working on a software project.

Extract important project knowledge that should be saved as memories. For each memory, identify:
1. Type: decision, preference, experience, convention, plan, or note
2. Title: A concise summary (max 100 chars)
3. Content: Detailed description
4. Reason: Why this is important or rationale
5. Tags: Relevant tags (e.g., architecture, database, auth)
6. Importance: Score from 0.0 to 1.0 (critical decisions = 0.9+, preferences = 0.5-0.7)
7. Confidence: How confident you are in this extraction (0.0 to 1.0)

Only extract significant information worth remembering for future sessions. Ignore casual chat.

Conversation:
{conversation_text}

Respond with a JSON array of extracted memories. Each memory should have this structure:
{{
  "type": "decision|preference|experience|convention|plan|note",
  "title": "Brief title",
  "content": "Detailed content",
  "reason": "Why this matters",
  "tags": ["tag1", "tag2"],
  "importance": 0.8,
  "confidence": 0.9
}}

If no significant memories found, return an empty array: []"""

            # Use LlamaIndex LLM to analyze
            llm = Settings.llm
            if not llm:
                raise ValueError("LLM not initialized in Settings")

            response = await llm.acomplete(extraction_prompt)
            response_text = str(response).strip()

            # Parse LLM response (extract JSON)
            memories = self._parse_llm_json_response(response_text)

            # Filter by confidence and auto-save if enabled
            auto_saved_count = 0
            extracted_memories = []
            suggestions = []

            for mem in memories:
                confidence = mem.get("confidence", 0.5)
                mem_data = {
                    "type": mem.get("type", "note"),
                    "title": mem.get("title", "Untitled"),
                    "content": mem.get("content", ""),
                    "reason": mem.get("reason"),
                    "tags": mem.get("tags", []),
                    "importance": mem.get("importance", 0.5)
                }

                if auto_save and confidence >= self.confidence_threshold:
                    # Auto-save high-confidence memories
                    result = await memory_store.add_memory(
                        project_id=project_id,
                        memory_type=mem_data["type"],
                        title=mem_data["title"],
                        content=mem_data["content"],
                        reason=mem_data["reason"],
                        tags=mem_data["tags"],
                        importance=mem_data["importance"],
                        metadata={"source": "conversation", "confidence": confidence}
                    )
                    if result.get("success"):
                        auto_saved_count += 1
                        extracted_memories.append({**mem_data, "memory_id": result["memory_id"], "auto_saved": True})
                else:
                    # Suggest for manual review
                    suggestions.append({**mem_data, "confidence": confidence})

            logger.success(f"Extracted {len(memories)} memories ({auto_saved_count} auto-saved)")

            return {
                "success": True,
                "extracted_memories": extracted_memories,
                "auto_saved_count": auto_saved_count,
                "suggestions": suggestions,
                "total_extracted": len(memories)
            }

        except Exception as e:
            logger.error(f"Failed to extract from conversation: {e}")
            return {
                "success": False,
                "error": str(e),
                "extracted_memories": [],
                "auto_saved_count": 0
            }

    async def extract_from_git_commit(
        self,
        project_id: str,
        commit_sha: str,
        commit_message: str,
        changed_files: List[str],
        auto_save: bool = False
    ) -> Dict[str, Any]:
        """
        Extract memories from git commit information using LLM analysis.

        Analyzes commit for:
        - Feature additions (decisions)
        - Bug fixes (experiences)
        - Refactoring (experiences/conventions)
        - Breaking changes (high importance decisions)

        Args:
            project_id: Project identifier
            commit_sha: Git commit SHA
            commit_message: Commit message (title + body)
            changed_files: List of file paths changed
            auto_save: If True, automatically save high-confidence memories

        Returns:
            Dict with extracted memories
        """
        try:
            logger.info(f"Extracting memories from commit {commit_sha[:8]}")

            # Classify commit type from message
            commit_type = self._classify_commit_type(commit_message)

            # Create extraction prompt
            extraction_prompt = f"""Analyze this git commit and extract important project knowledge.

Commit SHA: {commit_sha}
Commit Type: {commit_type}
Commit Message:
{commit_message}

Changed Files:
{chr(10).join(f'- {f}' for f in changed_files[:20])}
{"..." if len(changed_files) > 20 else ""}

Extract memories that represent important knowledge:
- For "feat" commits: architectural decisions, new features
- For "fix" commits: problems encountered and solutions
- For "refactor" commits: code improvements and rationale
- For "docs" commits: conventions and standards
- For breaking changes: critical decisions

Respond with a JSON array of memories (same format as before). Consider:
1. Type: Choose appropriate type based on commit nature
2. Title: Brief description of the change
3. Content: What was done and why
4. Reason: Technical rationale or problem solved
5. Tags: Extract from file paths and commit message
6. Importance: Breaking changes = 0.9+, features = 0.7+, fixes = 0.5+
7. Confidence: How significant is this commit

Return empty array [] if this is routine maintenance or trivial changes."""

            llm = Settings.llm
            if not llm:
                raise ValueError("LLM not initialized")

            response = await llm.acomplete(extraction_prompt)
            memories = self._parse_llm_json_response(str(response).strip())

            # Auto-save or suggest
            auto_saved_count = 0
            extracted_memories = []
            suggestions = []

            for mem in memories:
                confidence = mem.get("confidence", 0.5)
                mem_data = {
                    "type": mem.get("type", "note"),
                    "title": mem.get("title", commit_message.split('\n')[0][:100]),
                    "content": mem.get("content", ""),
                    "reason": mem.get("reason"),
                    "tags": mem.get("tags", []) + [commit_type],
                    "importance": mem.get("importance", 0.5),
                    "metadata": {
                        "source": "git_commit",
                        "commit_sha": commit_sha,
                        "changed_files": changed_files,
                        "confidence": confidence
                    }
                }

                if auto_save and confidence >= self.confidence_threshold:
                    result = await memory_store.add_memory(
                        project_id=project_id,
                        memory_type=mem_data["type"],
                        title=mem_data["title"],
                        content=mem_data["content"],
                        reason=mem_data["reason"],
                        tags=mem_data["tags"],
                        importance=mem_data["importance"],
                        metadata=mem_data["metadata"]
                    )
                    if result.get("success"):
                        auto_saved_count += 1
                        extracted_memories.append({**mem_data, "memory_id": result["memory_id"]})
                else:
                    suggestions.append({**mem_data, "confidence": confidence})

            logger.success(f"Extracted {len(memories)} memories from commit")

            return {
                "success": True,
                "extracted_memories": extracted_memories,
                "auto_saved_count": auto_saved_count,
                "suggestions": suggestions,
                "commit_type": commit_type
            }

        except Exception as e:
            logger.error(f"Failed to extract from commit: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def extract_from_code_comments(
        self,
        project_id: str,
        file_path: str,
        comments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Extract memories from code comments and docstrings.

        Identifies special markers:
        - "TODO:" → plan
        - "FIXME:" / "BUG:" → experience
        - "NOTE:" / "IMPORTANT:" → convention
        - "DECISION:" → decision (custom marker)

        Args:
            project_id: Project identifier
            file_path: Path to source file
            comments: Optional list of pre-extracted comments with line numbers.
                     If None, will parse the file automatically.

        Returns:
            Dict with extracted memories
        """
        try:
            logger.info(f"Extracting memories from code comments in {file_path}")

            # If comments not provided, extract them
            if comments is None:
                comments = self._extract_comments_from_file(file_path)

            if not comments:
                return {
                    "success": True,
                    "extracted_memories": [],
                    "message": "No comments found"
                }

            # Group comments by marker type
            extracted = []

            for comment in comments:
                text = comment.get("text", "")
                line_num = comment.get("line", 0)

                # Check for special markers
                memory_data = self._classify_comment(text, file_path, line_num)
                if memory_data:
                    extracted.append(memory_data)

            # If we have many comments, use LLM to analyze them together
            if len(extracted) > 5:
                logger.info(f"Using LLM to analyze {len(extracted)} comment markers")
                # Batch analyze for better context
                combined = self._combine_related_comments(extracted)
                extracted = combined

            # Save extracted memories
            saved_memories = []
            for mem_data in extracted:
                # Add file extension as tag if file has an extension
                file_tags = mem_data.get("tags", ["code-comment"])
                file_suffix = Path(file_path).suffix
                if file_suffix:
                    file_tags = file_tags + [file_suffix[1:]]
                
                result = await memory_store.add_memory(
                    project_id=project_id,
                    memory_type=mem_data["type"],
                    title=mem_data["title"],
                    content=mem_data["content"],
                    reason=mem_data.get("reason"),
                    tags=file_tags,
                    importance=mem_data.get("importance", 0.4),
                    related_refs=[f"ref://file/{file_path}#{mem_data.get('line', 0)}"],
                    metadata={
                        "source": "code_comment",
                        "file_path": file_path,
                        "line_number": mem_data.get("line", 0)
                    }
                )
                if result.get("success"):
                    saved_memories.append({**mem_data, "memory_id": result["memory_id"]})

            logger.success(f"Extracted {len(saved_memories)} memories from code comments")

            return {
                "success": True,
                "extracted_memories": saved_memories,
                "total_comments": len(comments),
                "total_extracted": len(saved_memories)
            }

        except Exception as e:
            logger.error(f"Failed to extract from code comments: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def suggest_memory_from_query(
        self,
        project_id: str,
        query: str,
        answer: str,
        source_nodes: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Suggest creating a memory based on a knowledge base query.

        Detects if the Q&A represents important knowledge that should be saved,
        such as:
        - Frequently asked questions
        - Important architectural information
        - Non-obvious solutions or workarounds

        Args:
            project_id: Project identifier
            query: User query
            answer: LLM answer
            source_nodes: Retrieved source nodes (optional)

        Returns:
            Dict with memory suggestion (not auto-saved, requires user confirmation)
        """
        try:
            logger.info(f"Analyzing query for memory suggestion: {query[:100]}")

            # Create analysis prompt
            prompt = f"""Analyze this Q&A from a code knowledge base query.

Query: {query}

Answer: {answer}

Determine if this Q&A represents important project knowledge worth saving as a memory.

Consider:
1. Is this a frequently asked or important question?
2. Does it reveal non-obvious information?
3. Is it about architecture, decisions, or important conventions?
4. Would this be valuable for future sessions?

If YES, extract a memory with:
- type: decision, preference, experience, convention, plan, or note
- title: Brief summary of the knowledge
- content: The important information from the answer
- reason: Why this is important
- tags: Relevant keywords
- importance: 0.0-1.0 (routine info = 0.3, important = 0.7+)
- should_save: true

If NO (routine question or trivial info), respond with:
{{"should_save": false, "reason": "explanation"}}

Respond with a single JSON object."""

            llm = Settings.llm
            if not llm:
                raise ValueError("LLM not initialized")

            response = await llm.acomplete(prompt)
            result = self._parse_llm_json_response(str(response).strip())

            if isinstance(result, list) and len(result) > 0:
                result = result[0]
            elif not isinstance(result, dict):
                result = {"should_save": False, "reason": "Could not parse LLM response"}

            should_save = result.get("should_save", False)

            if should_save:
                suggested_memory = {
                    "type": result.get("type", "note"),
                    "title": result.get("title", query[:self.MAX_TITLE_LENGTH]),
                    "content": result.get("content", answer[:self.MAX_CONTENT_LENGTH]),
                    "reason": result.get("reason", "Important Q&A from knowledge query"),
                    "tags": result.get("tags", ["query-based"]),
                    "importance": result.get("importance", 0.5)
                }

                logger.info(f"Suggested memory: {suggested_memory['title']}")

                return {
                    "success": True,
                    "should_save": True,
                    "suggested_memory": suggested_memory,
                    "query": query,
                    "answer_excerpt": answer[:self.MAX_STRING_EXCERPT_LENGTH]
                }
            else:
                return {
                    "success": True,
                    "should_save": False,
                    "reason": result.get("reason", "Not significant enough to save"),
                    "query": query
                }

        except Exception as e:
            logger.error(f"Failed to suggest memory from query: {e}")
            return {
                "success": False,
                "error": str(e),
                "should_save": False
            }

    async def batch_extract_from_repository(
        self,
        project_id: str,
        repo_path: str,
        max_commits: int = 50,
        file_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Batch extract memories from entire repository.

        Process:
        1. Scan recent git history for important commits
        2. Analyze README, CHANGELOG, docs
        3. Mine code comments from source files
        4. Generate project summary memory

        Args:
            project_id: Project identifier
            repo_path: Path to git repository
            max_commits: Maximum number of recent commits to analyze (default 50)
            file_patterns: List of file patterns to scan for comments (e.g., ["*.py", "*.js"])

        Returns:
            Dict with batch extraction results
        """
        try:
            logger.info(f"Starting batch extraction from repository: {repo_path}")

            repo_path_obj = Path(repo_path)
            if not repo_path_obj.exists():
                raise ValueError(f"Repository path not found: {repo_path}")

            extracted_memories = []
            by_source = {
                "git_commits": 0,
                "code_comments": 0,
                "documentation": 0
            }

            # 1. Extract from recent git commits
            logger.info(f"Analyzing last {max_commits} git commits...")
            commits = self._get_recent_commits(repo_path, max_commits)

            for commit in commits[:self.MAX_COMMITS_TO_PROCESS]:  # Focus on most recent commits for efficiency
                try:
                    result = await self.extract_from_git_commit(
                        project_id=project_id,
                        commit_sha=commit["sha"],
                        commit_message=commit["message"],
                        changed_files=commit["files"],
                        auto_save=True  # Auto-save significant commits
                    )
                    if result.get("success"):
                        count = result.get("auto_saved_count", 0)
                        by_source["git_commits"] += count
                        extracted_memories.extend(result.get("extracted_memories", []))
                except Exception as e:
                    logger.warning(f"Failed to extract from commit {commit['sha'][:8]}: {e}")

            # 2. Extract from code comments
            if file_patterns is None:
                file_patterns = ["*.py", "*.js", "*.ts", "*.java", "*.go", "*.rs"]

            logger.info(f"Scanning code comments in {file_patterns}...")
            source_files = []
            for pattern in file_patterns:
                source_files.extend(repo_path_obj.rglob(pattern))

            # Sample files to avoid overload
            sampled_files = list(source_files)[:self.MAX_FILES_TO_SAMPLE]

            for file_path in sampled_files:
                try:
                    result = await self.extract_from_code_comments(
                        project_id=project_id,
                        file_path=str(file_path)
                    )
                    if result.get("success"):
                        count = result.get("total_extracted", 0)
                        by_source["code_comments"] += count
                        extracted_memories.extend(result.get("extracted_memories", []))
                except Exception as e:
                    logger.warning(f"Failed to extract from {file_path.name}: {e}")

            # 3. Analyze documentation files
            logger.info("Analyzing documentation files...")
            doc_files = ["README.md", "CHANGELOG.md", "CONTRIBUTING.md", "CLAUDE.md"]

            for doc_name in doc_files:
                doc_path = repo_path_obj / doc_name
                if doc_path.exists():
                    try:
                        content = doc_path.read_text(encoding="utf-8")
                        # Extract key information from docs
                        doc_memory = self._extract_from_documentation(content, doc_name)
                        if doc_memory:
                            result = await memory_store.add_memory(
                                project_id=project_id,
                                **doc_memory,
                                metadata={"source": "documentation", "file": doc_name}
                            )
                            if result.get("success"):
                                by_source["documentation"] += 1
                                extracted_memories.append(doc_memory)
                    except Exception as e:
                        logger.warning(f"Failed to extract from {doc_name}: {e}")

            total_extracted = sum(by_source.values())

            logger.success(f"Batch extraction complete: {total_extracted} memories extracted")

            return {
                "success": True,
                "total_extracted": total_extracted,
                "by_source": by_source,
                "extracted_memories": extracted_memories,
                "repository": repo_path
            }

        except Exception as e:
            logger.error(f"Failed batch extraction: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_extracted": 0
            }


    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _format_conversation(self, conversation: List[Dict[str, str]]) -> str:
        """Format conversation for LLM analysis"""
        formatted = []
        for msg in conversation:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted.append(f"{role.upper()}: {content}\n")
        return "\n".join(formatted)

    def _parse_llm_json_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse JSON from LLM response, handling markdown code blocks"""
        import json

        # Remove markdown code blocks if present
        if "```json" in response_text:
            match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
            if match:
                response_text = match.group(1)
        elif "```" in response_text:
            match = re.search(r"```\s*(.*?)\s*```", response_text, re.DOTALL)
            if match:
                response_text = match.group(1)

        # Try to parse JSON
        try:
            result = json.loads(response_text)
            # Ensure it's a list
            if isinstance(result, dict):
                return [result]
            return result if isinstance(result, list) else []
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from LLM: {e}")
            logger.debug(f"Response text: {response_text[:self.MAX_STRING_EXCERPT_LENGTH]}")
            return []

    def _classify_commit_type(self, commit_message: str) -> str:
        """Classify commit type from conventional commit message"""
        msg_lower = commit_message.lower()
        first_line = commit_message.split('\n')[0].lower()

        # Conventional commits
        if first_line.startswith("feat"):
            return "feat"
        elif first_line.startswith("fix"):
            return "fix"
        elif first_line.startswith("refactor"):
            return "refactor"
        elif first_line.startswith("docs"):
            return "docs"
        elif first_line.startswith("test"):
            return "test"
        elif first_line.startswith("chore"):
            return "chore"
        elif "breaking" in msg_lower or "breaking change" in msg_lower:
            return "breaking"
        else:
            return "other"

    def _extract_comments_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract comments from Python source file using AST"""
        comments = []
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            return comments

        try:
            content = file_path_obj.read_text(encoding="utf-8")

            # For Python files, extract comments
            if file_path_obj.suffix == ".py":
                for line_num, line in enumerate(content.split('\n'), 1):
                    line_stripped = line.strip()
                    if line_stripped.startswith("#"):
                        comments.append({
                            "text": line_stripped[1:].strip(),
                            "line": line_num
                        })
            else:
                # For other files, simple pattern matching
                for line_num, line in enumerate(content.split('\n'), 1):
                    line_stripped = line.strip()
                    if "//" in line_stripped:
                        comment_text = line_stripped.split("//", 1)[1].strip()
                        comments.append({"text": comment_text, "line": line_num})

        except Exception as e:
            logger.warning(f"Failed to extract comments from {file_path}: {e}")

        return comments

    def _classify_comment(self, text: str, file_path: str, line_num: int) -> Optional[Dict[str, Any]]:
        """Classify comment and extract memory data if it has special markers"""
        text_upper = text.upper()

        # Check for special markers
        if text_upper.startswith("TODO:") or "TODO:" in text_upper:
            return {
                "type": "plan",
                "title": text.replace("TODO:", "").strip()[:100],
                "content": text,
                "importance": 0.4,
                "tags": ["todo"],
                "line": line_num
            }
        elif text_upper.startswith("FIXME:") or text_upper.startswith("BUG:"):
            return {
                "type": "experience",
                "title": text.replace("FIXME:", "").replace("BUG:", "").strip()[:100],
                "content": text,
                "importance": 0.6,
                "tags": ["bug", "fixme"],
                "line": line_num
            }
        elif text_upper.startswith("NOTE:") or text_upper.startswith("IMPORTANT:"):
            return {
                "type": "convention",
                "title": text.replace("NOTE:", "").replace("IMPORTANT:", "").strip()[:100],
                "content": text,
                "importance": 0.5,
                "tags": ["note"],
                "line": line_num
            }
        elif text_upper.startswith("DECISION:"):
            return {
                "type": "decision",
                "title": text.replace("DECISION:", "").strip()[:100],
                "content": text,
                "importance": 0.7,
                "tags": ["decision"],
                "line": line_num
            }

        return None

    def _combine_related_comments(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Combine related comments to avoid duplication"""
        # Simple grouping by type
        grouped = {}
        for comment in comments:
            mem_type = comment["type"]
            if mem_type not in grouped:
                grouped[mem_type] = []
            grouped[mem_type].append(comment)

        # Take top items per type by importance
        combined = []
        for mem_type, items in grouped.items():
            sorted_items = sorted(items, key=lambda x: x.get("importance", 0), reverse=True)
            combined.extend(sorted_items[:self.MAX_ITEMS_PER_TYPE])

        return combined

    def _get_recent_commits(self, repo_path: str, max_commits: int) -> List[Dict[str, Any]]:
        """Get recent commits from git repository"""
        commits = []
        try:
            # Get commit log
            result = subprocess.run(
                ["git", "log", f"-{max_commits}", "--pretty=format:%H|%s|%b"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )

            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue

                parts = line.split('|', 2)
                if len(parts) < 2:
                    continue

                sha = parts[0]
                subject = parts[1]
                body = parts[2] if len(parts) > 2 else ""

                # Get changed files for this commit
                files_result = subprocess.run(
                    ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                changed_files = [f.strip() for f in files_result.stdout.split('\n') if f.strip()]

                commits.append({
                    "sha": sha,
                    "message": f"{subject}\n{body}".strip(),
                    "files": changed_files
                })

        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to get git commits: {e}")
        except FileNotFoundError:
            logger.warning("Git not found in PATH")

        return commits

    def _extract_from_documentation(self, content: str, filename: str) -> Optional[Dict[str, Any]]:
        """Extract key information from documentation files"""
        # For README files, extract project overview
        if "README" in filename.upper():
            # Extract first few paragraphs as project overview
            lines = content.split('\n')
            description = []
            for line in lines[1:self.MAX_README_LINES]:  # Skip first line (usually title)
                if line.strip() and not line.startswith('#'):
                    description.append(line.strip())
                if len(description) >= 5:
                    break

            if description:
                return {
                    "memory_type": "note",
                    "title": f"Project Overview from {filename}",
                    "content": " ".join(description)[:self.MAX_CONTENT_LENGTH],
                    "reason": "Core project information from README",
                    "tags": ["documentation", "overview"],
                    "importance": 0.6
                }

        # For CHANGELOG, extract recent important changes
        elif "CHANGELOG" in filename.upper():
            return {
                "memory_type": "note",
                "title": "Project Changelog Summary",
                "content": content[:self.MAX_CONTENT_LENGTH],
                "reason": "Track project evolution and breaking changes",
                "tags": ["documentation", "changelog"],
                "importance": 0.5
            }

        return None


# ============================================================================
# Integration Hook for Knowledge Service
# ============================================================================

async def auto_save_query_as_memory(
    project_id: str,
    query: str,
    answer: str,
    threshold: float = 0.8
) -> Optional[str]:
    """
    Hook for knowledge service to auto-save important Q&A as memories.

    Can be called from query_knowledge endpoint to automatically save valuable Q&A.

    Args:
        project_id: Project identifier
        query: User query
        answer: LLM answer
        threshold: Confidence threshold for auto-saving (default 0.8)

    Returns:
        memory_id if saved, None otherwise
    """
    try:
        # Use memory extractor to analyze the query
        result = await memory_extractor.suggest_memory_from_query(
            project_id=project_id,
            query=query,
            answer=answer
        )

        if not result.get("success"):
            return None

        should_save = result.get("should_save", False)
        suggested_memory = result.get("suggested_memory")

        if should_save and suggested_memory:
            # Get importance from suggestion
            importance = suggested_memory.get("importance", 0.5)

            # Only auto-save if importance meets threshold
            if importance >= threshold:
                save_result = await memory_store.add_memory(
                    project_id=project_id,
                    memory_type=suggested_memory["type"],
                    title=suggested_memory["title"],
                    content=suggested_memory["content"],
                    reason=suggested_memory.get("reason"),
                    tags=suggested_memory.get("tags", []),
                    importance=importance,
                    metadata={"source": "auto_query", "query": query[:self.MAX_STRING_EXCERPT_LENGTH]}
                )

                if save_result.get("success"):
                    memory_id = save_result.get("memory_id")
                    logger.info(f"Auto-saved query as memory: {memory_id}")
                    return memory_id

        return None

    except Exception as e:
        logger.error(f"Failed to auto-save query as memory: {e}")
        return None


# Global instance
memory_extractor = MemoryExtractor()
