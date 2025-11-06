#!/usr/bin/env python3
"""
MCP Server Entry Point

This is a thin wrapper for backward compatibility.
The actual implementation is in src.codebase_rag.server.mcp
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Main entry point"""
    from src.codebase_rag.server.mcp import main as mcp_main
    return mcp_main()


if __name__ == "__main__":
    main()
