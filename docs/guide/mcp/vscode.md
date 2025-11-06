# VS Code MCP Extension Setup

Complete guide to integrating Code Graph Knowledge System with Visual Studio Code using the MCP (Model Context Protocol) extension.

## Overview

VS Code MCP integration allows you to use Code Graph Knowledge System tools directly within your editor:

- **Inline queries**: Query knowledge base from the editor
- **Code analysis**: Analyze code without leaving VS Code
- **Memory management**: Save and retrieve project memories
- **Context awareness**: AI assistant with your codebase context
- **Seamless workflow**: No context switching

## Prerequisites

### 1. Visual Studio Code

Download and install VS Code:

- **Download**: https://code.visualstudio.com/download
- **Minimum version**: 1.85.0+
- **Platforms**: Windows, macOS, Linux

### 2. MCP Extension

Install the MCP extension for VS Code:

**Option 1: VS Code Marketplace**
1. Open VS Code
2. Press `Ctrl+Shift+X` (Windows/Linux) or `Cmd+Shift+X` (macOS)
3. Search for "Model Context Protocol" or "MCP"
4. Click Install

**Option 2: Command Line**
```bash
code --install-extension anthropic.mcp
```

**Option 3: Extensions View**
- Open Command Palette: `Ctrl+Shift+P` / `Cmd+Shift+P`
- Type: "Extensions: Install Extensions"
- Search: "MCP"
- Install

### 3. Code Graph Knowledge System

Ensure the MCP server is accessible:

```bash
# Running locally
cd /path/to/codebase-rag
python start_mcp.py

# Or via Docker
docker-compose -f docker/docker-compose.full.yml up -d

# Verify
ps aux | grep start_mcp.py
```

### 4. Python Environment

```bash
# Python 3.10+ required
python --version

# Install dependencies
cd /path/to/codebase-rag
pip install -e .

# Or with uv
uv pip install -e .
```

## Configuration

### Method 1: Settings UI

1. **Open Settings**:
   - Press `Ctrl+,` (Windows/Linux) or `Cmd+,` (macOS)
   - Or: File → Preferences → Settings

2. **Search for MCP**:
   - Type "mcp" in settings search
   - Look for "MCP: Servers" section

3. **Add Server**:
   - Click "Edit in settings.json"
   - Add configuration (see examples below)

### Method 2: settings.json

**Open settings.json**:
- Command Palette: `Ctrl+Shift+P` / `Cmd+Shift+P`
- Type: "Preferences: Open User Settings (JSON)"
- Or: "Preferences: Open Workspace Settings (JSON)"

**Basic Configuration**:

```json
{
  "mcp.servers": {
    "code-graph": {
      "command": "python",
      "args": ["/absolute/path/to/codebase-rag/start_mcp.py"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/codebase-rag"
      }
    }
  }
}
```

## Configuration Examples

### Example 1: Full Mode with Environment Variables

```json
{
  "mcp.servers": {
    "code-graph-full": {
      "command": "python",
      "args": ["/Users/developer/projects/codebase-rag/start_mcp.py"],
      "env": {
        "PYTHONPATH": "/Users/developer/projects/codebase-rag",
        "DEPLOYMENT_MODE": "full",
        "ENABLE_KNOWLEDGE_RAG": "true",
        "ENABLE_AUTO_EXTRACTION": "true",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "mypassword",
        "LLM_PROVIDER": "ollama",
        "OLLAMA_HOST": "http://localhost:11434",
        "OLLAMA_MODEL": "llama3.2",
        "EMBEDDING_PROVIDER": "ollama",
        "OLLAMA_EMBEDDING_MODEL": "nomic-embed-text"
      }
    }
  }
}
```

### Example 2: Using uv

```json
{
  "mcp.servers": {
    "code-graph": {
      "command": "uv",
      "args": ["run", "mcp_server"],
      "cwd": "/absolute/path/to/codebase-rag"
    }
  }
}
```

### Example 3: Docker Container

```json
{
  "mcp.servers": {
    "code-graph-docker": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "codebase-rag-mcp",
        "python",
        "/app/start_mcp.py"
      ],
      "env": {
        "DOCKER_HOST": "unix:///var/run/docker.sock"
      }
    }
  }
}
```

### Example 4: Remote Server via SSH

```json
{
  "mcp.servers": {
    "code-graph-remote": {
      "command": "ssh",
      "args": [
        "user@remote-server",
        "cd /path/to/codebase-rag && python start_mcp.py"
      ]
    }
  }
}
```

### Example 5: Workspace-Specific Configuration

Save in `.vscode/settings.json` within your project:

```json
{
  "mcp.servers": {
    "project-knowledge": {
      "command": "python",
      "args": ["${workspaceFolder}/../codebase-rag/start_mcp.py"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/../codebase-rag",
        "NEO4J_DATABASE": "project_specific_db"
      }
    }
  }
}
```

### Example 6: Multiple Servers

```json
{
  "mcp.servers": {
    "project-a-knowledge": {
      "command": "python",
      "args": ["/path/to/project-a/codebase-rag/start_mcp.py"],
      "env": {
        "NEO4J_DATABASE": "project_a"
      }
    },
    "project-b-knowledge": {
      "command": "python",
      "args": ["/path/to/project-b/codebase-rag/start_mcp.py"],
      "env": {
        "NEO4J_DATABASE": "project_b"
      }
    }
  }
}
```

## Verification

### Check MCP Connection

1. **Open Command Palette**: `Ctrl+Shift+P` / `Cmd+Shift+P`

2. **Run**: "MCP: Show Connected Servers"

3. **Expected output**:
   - Server name: "code-graph" (or your configured name)
   - Status: "Connected"
   - Tools: 20-30 tools listed

### Test Tool Access

1. **Open Command Palette**

2. **Run**: "MCP: List Available Tools"

3. **Verify tools** are listed:
   - `query_knowledge`
   - `add_memory`
   - `code_graph_ingest_repo`
   - `search_memories`
   - etc.

### Test Basic Query

1. **Open Command Palette**

2. **Run**: "MCP: Execute Tool"

3. **Select**: `get_statistics`

4. **Expected**: System statistics displayed

## Usage Patterns

### 1. Query Knowledge Base

**Method A: Command Palette**
1. Press `Ctrl+Shift+P` / `Cmd+Shift+P`
2. Type: "MCP: Execute Tool"
3. Select: `query_knowledge`
4. Enter question: "How do I configure Docker?"
5. View results

**Method B: Quick Input**
1. Select text in editor
2. Right-click → "Query Knowledge Base"
3. Results appear in panel

**Method C: Keyboard Shortcut**
```json
// Add to keybindings.json
{
  "key": "ctrl+shift+k",
  "command": "mcp.executeQuery",
  "args": {
    "tool": "query_knowledge"
  }
}
```

### 2. Search Code

**Method A: Search Current Project**
1. Open Command Palette
2. "MCP: Execute Tool" → `code_graph_fulltext_search`
3. Enter search term
4. View matching files

**Method B: Context Menu**
1. Right-click in editor
2. "Search Code Graph" → enters selected text
3. View results

### 3. Add Memory

**Interactive Mode**:
1. Command Palette → "MCP: Add Memory"
2. Fill in prompts:
   - Project ID: `myproject`
   - Type: `decision`
   - Title: "Use PostgreSQL"
   - Content: "Selected PostgreSQL for main database"
   - Reason: "Better JSON support"
   - Importance: `0.9`
   - Tags: `database, architecture`

**Quick Mode**:
1. Select text in editor
2. Right-click → "Save as Memory"
3. Choose memory type
4. Confirm

### 4. Analyze Code Impact

1. Open file to analyze
2. Command Palette → "MCP: Execute Tool"
3. Select: `code_graph_impact_analysis`
4. Enter file path (or current file)
5. View impact report

### 5. Monitor Tasks

**For async operations**:
1. Submit directory processing
2. Get task_id
3. Command Palette → "MCP: Watch Task"
4. Enter task_id
5. View real-time progress

## Workspace Integration

### Project-Specific Configuration

Create `.vscode/settings.json` in your project:

```json
{
  "mcp.servers": {
    "this-project": {
      "command": "python",
      "args": ["${workspaceFolder}/.mcp/start_mcp.py"],
      "env": {
        "PROJECT_NAME": "${workspaceFolderBasename}",
        "NEO4J_DATABASE": "${workspaceFolderBasename}_db"
      }
    }
  },
  "mcp.defaultServer": "this-project"
}
```

### Task Integration

Add MCP tasks to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Index Codebase",
      "type": "shell",
      "command": "python",
      "args": [
        "-c",
        "import asyncio; from mcp_tools import handle_code_graph_ingest_repo; asyncio.run(handle_code_graph_ingest_repo({'repo_path': '${workspaceFolder}', 'mode': 'incremental'}))"
      ],
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "Query Knowledge",
      "type": "shell",
      "command": "python",
      "args": [
        "-c",
        "import sys; from mcp_tools import handle_query_knowledge; print(handle_query_knowledge({'question': sys.argv[1]}))",
        "${input:question}"
      ]
    }
  ],
  "inputs": [
    {
      "id": "question",
      "type": "promptString",
      "description": "Enter your question:"
    }
  ]
}
```

### Keyboard Shortcuts

Add to `keybindings.json`:

```json
[
  {
    "key": "ctrl+shift+k",
    "command": "mcp.queryKnowledge",
    "when": "editorTextFocus"
  },
  {
    "key": "ctrl+shift+m",
    "command": "mcp.addMemory",
    "when": "editorHasSelection"
  },
  {
    "key": "ctrl+shift+i",
    "command": "mcp.ingestRepository",
    "when": "workspaceFolderCount > 0"
  },
  {
    "key": "ctrl+shift+s",
    "command": "mcp.searchCode"
  }
]
```

## Advanced Features

### Snippets Integration

Create custom snippets that use MCP tools:

`.vscode/snippets.code-snippets`:
```json
{
  "Query Knowledge": {
    "prefix": "mcp-query",
    "body": [
      "// Query: ${1:question}",
      "// Answer: ${2:Use MCP to query}",
      "$0"
    ],
    "description": "Insert MCP query placeholder"
  },
  "Add Memory": {
    "prefix": "mcp-memory",
    "body": [
      "// MEMORY: ${1:title}",
      "// Type: ${2|decision,preference,experience,convention|}",
      "// Importance: ${3:0.8}",
      "// ${4:description}",
      "$0"
    ],
    "description": "Memory marker for auto-extraction"
  }
}
```

### Extension Integration

Create custom VS Code extension:

```typescript
import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
  // Register command to query knowledge
  let disposable = vscode.commands.registerCommand(
    'extension.queryKnowledge',
    async () => {
      const question = await vscode.window.showInputBox({
        prompt: 'Enter your question'
      });

      if (question) {
        const result = await vscode.commands.executeCommand(
          'mcp.executeTool',
          {
            server: 'code-graph',
            tool: 'query_knowledge',
            args: { question, mode: 'hybrid' }
          }
        );

        // Display result
        const panel = vscode.window.createWebviewPanel(
          'mcpResult',
          'Knowledge Query Result',
          vscode.ViewColumn.Two,
          {}
        );
        panel.webview.html = formatResult(result);
      }
    }
  );

  context.subscriptions.push(disposable);
}
```

### Code Lens Provider

Add inline code lenses:

```typescript
export class MCPCodeLensProvider implements vscode.CodeLensProvider {
  provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
    const codeLenses: vscode.CodeLens[] = [];
    const text = document.getText();

    // Find memory markers
    const memoryRegex = /\/\/ MEMORY: (.+)/g;
    let match;

    while ((match = memoryRegex.exec(text)) !== null) {
      const line = document.lineAt(
        document.positionAt(match.index).line
      );

      codeLenses.push(
        new vscode.CodeLens(line.range, {
          title: '💾 Save as Memory',
          command: 'mcp.addMemory',
          arguments: [match[1]]
        })
      );
    }

    return codeLenses;
  }
}
```

## Best Practices

### 1. Workspace Configuration

Use workspace settings for project-specific config:

```json
// .vscode/settings.json
{
  "mcp.servers": {
    "local": {
      "command": "python",
      "args": ["${workspaceFolder}/../codebase-rag/start_mcp.py"]
    }
  },
  "mcp.autoConnect": true,
  "mcp.logLevel": "info"
}
```

### 2. Environment Management

Use `.env` files for sensitive data:

```bash
# .env (in codebase-rag directory)
NEO4J_PASSWORD=secret
OPENAI_API_KEY=sk-...
```

Reference in VS Code:
```json
{
  "mcp.servers": {
    "code-graph": {
      "command": "python",
      "args": ["${workspaceFolder}/start_mcp.py"],
      "envFile": "${workspaceFolder}/.env"
    }
  }
}
```

### 3. Multi-Project Setup

For multiple projects, use workspace folders:

```json
{
  "folders": [
    {
      "path": "/path/to/project-a",
      "name": "Project A"
    },
    {
      "path": "/path/to/project-b",
      "name": "Project B"
    }
  ],
  "settings": {
    "mcp.servers": {
      "project-a": {
        "command": "python",
        "args": ["/path/to/project-a/codebase-rag/start_mcp.py"]
      },
      "project-b": {
        "command": "python",
        "args": ["/path/to/project-b/codebase-rag/start_mcp.py"]
      }
    }
  }
}
```

### 4. Performance Optimization

**Lazy Loading**:
```json
{
  "mcp.servers": {
    "code-graph": {
      "command": "python",
      "args": ["start_mcp.py"],
      "lazyLoad": true,  // Only start when needed
      "timeout": 30000
    }
  }
}
```

**Connection Pooling**:
```json
{
  "mcp.connectionPool": {
    "maxConnections": 5,
    "idleTimeout": 60000
  }
}
```

## Troubleshooting

### Issue: Server Not Connecting

**Symptoms**:
- "Failed to connect to MCP server"
- No tools available

**Solutions**:

1. **Check configuration syntax**:
   ```bash
   # Validate JSON
   python -m json.tool .vscode/settings.json
   ```

2. **Verify command works**:
   ```bash
   cd /path/to/codebase-rag
   python start_mcp.py
   # Should not exit immediately
   ```

3. **Check VS Code output**:
   - View → Output
   - Select "MCP" from dropdown
   - Check for error messages

4. **Reload window**:
   - Command Palette → "Developer: Reload Window"

### Issue: Tools Failing

**Symptoms**:
- Tool calls return errors
- Timeout messages

**Solutions**:

1. **Increase timeout**:
   ```json
   {
     "mcp.servers": {
       "code-graph": {
         "timeout": 60000  // 60 seconds
       }
     }
   }
   ```

2. **Check backend services**:
   ```bash
   # Neo4j
   cypher-shell "RETURN 1"

   # Ollama (if using)
   curl http://localhost:11434/api/tags
   ```

3. **View MCP server logs**:
   ```bash
   tail -f /path/to/codebase-rag/mcp_server.log
   ```

### Issue: Permission Denied

**Symptoms**:
- Cannot start MCP server
- Permission errors in output

**Solutions**:

1. **Fix file permissions**:
   ```bash
   chmod +x start_mcp.py
   ```

2. **Check VS Code has access**:
   ```bash
   # macOS: Grant Full Disk Access
   System Preferences → Security & Privacy → Full Disk Access → Add VS Code
   ```

3. **Run as correct user**:
   ```bash
   whoami
   # Ensure matches Neo4j user
   ```

### Issue: Slow Performance

**Symptoms**:
- Long delays for tool calls
- VS Code freezing

**Solutions**:

1. **Use async mode**:
   - Directory processing
   - Large document ingestion

2. **Reduce query scope**:
   ```json
   {
     "question": "specific query",
     "top_k": 3  // Reduce from default 5
   }
   ```

3. **Enable caching**:
   ```bash
   # In .env
   ENABLE_QUERY_CACHE=true
   CACHE_TTL=3600
   ```

## Integration with Other Extensions

### GitHub Copilot

Combine with Copilot:

```json
{
  "github.copilot.advanced": {
    "contextSources": ["mcp-code-graph"]
  }
}
```

### GitLens

Extract memories from git commits:

```json
{
  "gitlens.advanced.messages": {
    "suppressCommitNotFoundWarning": true
  },
  "mcp.git.autoExtract": true
}
```

### REST Client

Test MCP tools via HTTP:

```http
### Query Knowledge
POST http://localhost:8000/api/v1/knowledge/query
Content-Type: application/json

{
  "question": "How do I configure Docker?",
  "mode": "hybrid"
}
```

## Next Steps

- **[MCP Overview](overview.md)**: Learn about MCP protocol
- **[Claude Desktop Setup](claude-desktop.md)**: Configure Claude Desktop
- **[Knowledge RAG](../knowledge/overview.md)**: Use query tools effectively
- **[Code Graph](../code-graph/overview.md)**: Analyze your codebase

## Additional Resources

- **VS Code MCP Extension**: https://marketplace.visualstudio.com/items?itemName=anthropic.mcp
- **MCP Documentation**: https://modelcontextprotocol.io/
- **VS Code API**: https://code.visualstudio.com/api
- **Extension Development**: https://code.visualstudio.com/api/get-started/your-first-extension
