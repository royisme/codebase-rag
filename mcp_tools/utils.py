"""
Utility Functions for MCP Server v2

This module contains helper functions for formatting results
and other utility operations.
"""

import json
from typing import Dict, Any


def format_result(result: Dict[str, Any]) -> str:
    """
    Format result dictionary for display.

    Args:
        result: Result dictionary from handler functions

    Returns:
        Formatted string representation of the result
    """

    if not result.get("success"):
        return f"❌ Error: {result.get('error', 'Unknown error')}"

    # Format based on content
    if "answer" in result:
        # Query result
        output = [f"Answer: {result['answer']}\n"]
        if "source_nodes" in result:
            source_nodes = result["source_nodes"]
            output.append(f"\nSources ({len(source_nodes)} nodes):")
            for i, node in enumerate(source_nodes[:5], 1):
                output.append(f"{i}. {node.get('text', '')[:100]}...")
        return "\n".join(output)

    elif "results" in result:
        # Search result
        results = result["results"]
        if not results:
            return "No results found."

        output = [f"Found {len(results)} results:\n"]
        for i, r in enumerate(results[:10], 1):
            output.append(f"{i}. Score: {r.get('score', 0):.3f}")
            output.append(f"   {r.get('text', '')[:100]}...\n")
        return "\n".join(output)

    elif "memories" in result:
        # Memory search
        memories = result["memories"]
        if not memories:
            return "No memories found."

        output = [f"Found {result.get('total_count', 0)} memories:\n"]
        for i, mem in enumerate(memories, 1):
            output.append(f"{i}. [{mem['type']}] {mem['title']}")
            output.append(f"   Importance: {mem.get('importance', 0.5):.2f}")
            if mem.get('tags'):
                output.append(f"   Tags: {', '.join(mem['tags'])}")
            output.append(f"   ID: {mem['id']}\n")
        return "\n".join(output)

    elif "memory" in result:
        # Single memory
        mem = result["memory"]
        output = [
            f"Memory: {mem['title']}",
            f"Type: {mem['type']}",
            f"Importance: {mem.get('importance', 0.5):.2f}",
            f"\nContent: {mem['content']}"
        ]
        if mem.get('reason'):
            output.append(f"\nReason: {mem['reason']}")
        if mem.get('tags'):
            output.append(f"\nTags: {', '.join(mem['tags'])}")
        output.append(f"\nID: {mem['id']}")
        return "\n".join(output)

    elif "nodes" in result:
        # Code graph result
        nodes = result["nodes"]
        if not nodes:
            return "No nodes found."

        output = [f"Found {len(nodes)} nodes:\n"]
        for i, node in enumerate(nodes[:10], 1):
            output.append(f"{i}. {node.get('path', node.get('name', 'Unknown'))}")
            if node.get('score'):
                output.append(f"   Score: {node['score']:.3f}")
            if node.get('ref'):
                output.append(f"   Ref: {node['ref']}")
            output.append("")
        return "\n".join(output)

    elif "items" in result:
        # Context pack
        items = result["items"]
        budget_used = result.get("budget_used", 0)
        budget_limit = result.get("budget_limit", 0)

        output = [
            f"Context Pack ({budget_used}/{budget_limit} tokens)\n",
            f"Items: {len(items)}\n"
        ]

        for item in items:
            output.append(f"[{item['kind']}] {item['title']}")
            if item.get('summary'):
                output.append(f"  {item['summary'][:100]}...")
            output.append(f"  Ref: {item['ref']}\n")

        return "\n".join(output)

    elif "tasks" in result and isinstance(result["tasks"], list):
        # Task list
        tasks = result["tasks"]
        if not tasks:
            return "No tasks found."

        output = [f"Tasks ({len(tasks)}):\n"]
        for task in tasks:
            output.append(f"- {task['task_id']}: {task['status']}")
            output.append(f"  Created: {task['created_at']}")
        return "\n".join(output)

    elif "stats" in result:
        # Queue stats
        stats = result["stats"]
        output = [
            "Queue Statistics:",
            f"Pending: {stats.get('pending', 0)}",
            f"Running: {stats.get('running', 0)}",
            f"Completed: {stats.get('completed', 0)}",
            f"Failed: {stats.get('failed', 0)}"
        ]
        return "\n".join(output)

    else:
        # Generic success
        return f"✅ Success\n{json.dumps(result, indent=2)}"
