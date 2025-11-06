# Docker Image Optimization

## Problem
Previously, Docker images were **>5GB** due to unnecessary CUDA/GPU dependencies:
- PyTorch with CUDA: ~2-3 GB
- NVIDIA CUDA libraries: 15 packages
- Sentence Transformers
- Other unused ML dependencies

## Solution
Moved heavy dependencies to **optional extras**:

### Core Dependencies (Default)
```bash
# Minimal, production-ready (default providers: Ollama, Gemini)
pip install -e .
```

### Optional Dependencies

#### HuggingFace Embeddings (adds ~2GB)
```bash
pip install -e ".[huggingface]"
```

#### Milvus Vector Database
```bash
pip install -e ".[milvus]"
```

#### OpenRouter LLM Support
```bash
pip install -e ".[openrouter]"
```

### All Optional Features
```bash
pip install -e ".[huggingface,milvus,openrouter]"
```

## Results
- **Image size reduction**: ~60-70% smaller (~5GB → ~1.5GB)
- **Build time**: ~50% faster (layer caching + fewer deps)
- **Dependencies**: 564 → 379 lines (-32.9%)
- **NVIDIA packages**: 15 → 0 ✅

## Dockerfile Optimizations

The Dockerfile was also optimized to leverage these changes:

### Before
```dockerfile
# ❌ Problem: Installing from pyproject.toml with all dependencies
COPY pyproject.toml ./
RUN uv pip install --system -e .

# ❌ Problem: Copying ALL binaries including build tools
COPY --from=builder /usr/local/bin /usr/local/bin
```

### After
```dockerfile
# ✅ Better: Use pre-compiled requirements.txt (no CUDA)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Better: Copy only necessary entry points
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/
```

### Key Improvements
1. **Uses requirements.txt** instead of pyproject.toml → no dependency resolution at build time
2. **Better layer caching** → requirements.txt changes less frequently than pyproject.toml
3. **Selective binary copying** → excludes uv, pip-compile, gcc, and other build tools
4. **Production mode** → not using editable mode for dependencies (only for local package)

## Default Configuration
The default setup uses:
- **LLM**: Ollama (local, no API key needed)
- **Embeddings**: Ollama (nomic-embed-text)
- **Vector DB**: Neo4j (built-in)

Change providers via environment variables:
```bash
EMBEDDING_PROVIDER=ollama|gemini|huggingface|openrouter
LLM_PROVIDER=ollama|gemini|openrouter
```

## Migration Guide
If you were using HuggingFace embeddings:
```bash
# Option 1: Switch to Ollama (recommended)
EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Option 2: Keep HuggingFace (install extra)
pip install -e ".[huggingface]"
EMBEDDING_PROVIDER=huggingface
```
