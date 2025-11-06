"""
Main entry point for codebase-rag package.

Usage:
    python -m codebase_rag [--web|--mcp|--version]
"""

import sys
import argparse


def main():
    """Main entry point for the package."""
    parser = argparse.ArgumentParser(
        description="Codebase RAG - Code Knowledge Graph and RAG System"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start web server (FastAPI)",
    )
    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Start MCP server",
    )

    args = parser.parse_args()

    if args.version:
        from src.codebase_rag import __version__
        print(f"codebase-rag version {__version__}")
        return 0

    if args.mcp:
        # Run MCP server
        print("Starting MCP server...")
        from src.codebase_rag.server.mcp import main as mcp_main
        return mcp_main()

    if args.web or not any([args.web, args.mcp, args.version]):
        # Default: start web server
        print("Starting web server...")
        from src.codebase_rag.server.web import main as web_main
        return web_main()

    return 0


if __name__ == "__main__":
    sys.exit(main())
