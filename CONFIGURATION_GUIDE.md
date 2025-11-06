# Configuration Guide - Next Steps

This guide walks you through the required configuration to complete the deployment and documentation setup.

---

## 🎯 Configuration Checklist

Follow these steps in order:

- [ ] 1. Configure GitHub Repository Secrets
- [ ] 2. Enable GitHub Pages
- [ ] 3. Configure DNS for docs.vantagecraft.dev
- [ ] 4. Test Docker builds locally (optional)
- [ ] 5. Verify CI/CD workflows
- [ ] 6. Submit to Docker MCP Registry

---

## 1️⃣ Configure GitHub Repository Secrets

### Docker Hub Token

The GitHub Actions workflow needs permission to push Docker images to Docker Hub.

**Step 1: Create Docker Hub Access Token**

1. Go to https://hub.docker.com/settings/security
2. Click "New Access Token"
3. Name: `github-actions-codebase-rag`
4. Permissions: **Read, Write, Delete**
5. Click "Generate"
6. **Copy the token** (you won't see it again!)

**Step 2: Add Secret to GitHub**

1. Go to your repository: https://github.com/royisme/codebase-rag
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `DOCKER_HUB_TOKEN`
5. Secret: Paste the token from Docker Hub
6. Click **Add secret**

✅ **Verification**: The secret should appear in the list (value hidden)

---

## 2️⃣ Enable GitHub Pages

Enable GitHub Pages to automatically deploy documentation.

**Step 1: Enable GitHub Pages**

1. Go to: https://github.com/royisme/codebase-rag/settings/pages
2. Under **Source**, select: **GitHub Actions**
3. Click **Save**

**Step 2: Verify Workflow Permissions**

1. Go to: https://github.com/royisme/codebase-rag/settings/actions
2. Scroll to **Workflow permissions**
3. Select: **Read and write permissions**
4. Check: **Allow GitHub Actions to create and approve pull requests**
5. Click **Save**

✅ **Verification**: Next push will trigger documentation deployment

---

## 3️⃣ Configure DNS for code-graph.vantagecraft.dev

Point your documentation subdomain to GitHub Pages.

### Option A: Using CNAME (Recommended)

**If vantagecraft.dev is on Cloudflare, Namecheap, etc:**

1. Go to your DNS provider's control panel
2. Add a **CNAME record**:
   ```
   Type: CNAME
   Name: code-graph
   Target: royisme.github.io
   TTL: 3600 (or Auto)
   Proxy: Off (disable Cloudflare proxy initially)
   ```
3. Save the record

**DNS Propagation**: Can take 5 minutes to 48 hours

**Why code-graph instead of docs?**
- This allows you to use different subdomains for different projects
- Example: `project-a.vantagecraft.dev`, `project-b.vantagecraft.dev`
- Keeps your main `docs` subdomain available for a unified documentation portal

### Option B: Using A Records (Alternative)

If CNAME doesn't work, use A records:

```
Type: A
Name: docs
Value: 185.199.108.153
TTL: 3600

Type: A
Name: docs
Value: 185.199.109.153
TTL: 3600

Type: A
Name: docs
Value: 185.199.110.153
TTL: 3600

Type: A
Name: docs
Value: 185.199.111.153
TTL: 3600
```

### Verify DNS Configuration

After adding DNS records, verify:

```bash
# Check CNAME
nslookup code-graph.vantagecraft.dev

# Or use dig
dig code-graph.vantagecraft.dev

# Should return:
# code-graph.vantagecraft.dev CNAME royisme.github.io
```

✅ **Verification**: DNS lookup returns correct target

### Configure Custom Domain in GitHub

1. Go to: https://github.com/royisme/codebase-rag/settings/pages
2. Under **Custom domain**, enter: `code-graph.vantagecraft.dev`
3. Click **Save**
4. Wait for DNS check (may take a few minutes)
5. Once verified, check **Enforce HTTPS** (recommended)

✅ **Verification**: Green checkmark appears, HTTPS enabled

---

## 4️⃣ Test Docker Builds Locally (Optional)

Before relying on CI/CD, test builds locally.

### Test Minimal Build

```bash
cd /path/to/codebase-rag

# Build minimal image
docker build -f docker/Dockerfile.minimal -t royisme/codebase-rag:minimal-test .

# Test it runs
docker run --rm royisme/codebase-rag:minimal-test python -c "print('Minimal OK')"
```

### Test Standard Build

```bash
# Build standard image
docker build -f docker/Dockerfile.standard -t royisme/codebase-rag:standard-test .

# Test
docker run --rm royisme/codebase-rag:standard-test python -c "print('Standard OK')"
```

### Test Full Build

```bash
# Build full image
docker build -f docker/Dockerfile.full -t royisme/codebase-rag:full-test .

# Test
docker run --rm royisme/codebase-rag:full-test python -c "print('Full OK')"
```

### Test with Docker Compose

```bash
# Test minimal deployment
make docker-build-minimal
make docker-minimal

# Check health
curl http://localhost:8000/api/v1/health

# Stop
make docker-stop
```

✅ **Verification**: All builds succeed, services start correctly

---

## 5️⃣ Verify CI/CD Workflows

### Trigger GitHub Actions

**Option A: Push to Main (Recommended)**

```bash
# Merge your branch to main
# Or create a pull request and merge it
```

**Option B: Manual Trigger**

1. Go to: https://github.com/royisme/codebase-rag/actions
2. Select **Build and Push Docker Images**
3. Click **Run workflow** → **Run workflow**

### Monitor Workflow Progress

1. Go to: https://github.com/royisme/codebase-rag/actions
2. Watch the running workflow
3. Check each job:
   - ✅ build-minimal
   - ✅ build-standard
   - ✅ build-full

**Expected Duration**: ~10-15 minutes per image

### Verify Docker Hub Images

Once workflows complete:

```bash
# Pull the images
docker pull royisme/codebase-rag:minimal
docker pull royisme/codebase-rag:standard
docker pull royisme/codebase-rag:full

# Check they exist
docker images | grep codebase-rag
```

Or check on Docker Hub:
- https://hub.docker.com/r/royisme/codebase-rag/tags

✅ **Verification**: All 3 images available on Docker Hub

### Verify Documentation Deployment

1. Go to: https://github.com/royisme/codebase-rag/actions
2. Check **Deploy Documentation** workflow
3. Once complete, visit: https://docs.vantagecraft.dev

✅ **Verification**: Documentation site loads correctly

---

## 6️⃣ Submit to Docker MCP Registry

Once images are published and tested:

### Prepare Submission

```bash
# Fork the MCP registry
# Go to: https://github.com/docker/mcp-registry
# Click "Fork"

# Clone your fork
git clone https://github.com/YOUR_USERNAME/mcp-registry.git
cd mcp-registry
```

### Copy Submission Files

```bash
# Copy the three variants
cp -r /path/to/codebase-rag/mcp-registry-submission/codebase-rag-minimal servers/
cp -r /path/to/codebase-rag/mcp-registry-submission/codebase-rag-standard servers/
cp -r /path/to/codebase-rag/mcp-registry-submission/codebase-rag-full servers/

# Verify structure
ls -la servers/codebase-rag-*
```

### Create Pull Request

```bash
# Create branch
git checkout -b add-codebase-rag

# Commit
git add servers/codebase-rag-*
git commit -m "Add Code Graph Knowledge System (3 variants: minimal, standard, full)"

# Push
git push origin add-codebase-rag
```

### Open PR on GitHub

1. Go to your fork on GitHub
2. Click "Contribute" → "Open pull request"
3. Use the template in `mcp-registry-submission/SUBMISSION_GUIDE.md`
4. Submit!

✅ **Verification**: PR created, awaiting review

---

## 🔍 Verification Summary

After completing all steps, verify:

```bash
# 1. Docker images available
docker pull royisme/codebase-rag:minimal
docker pull royisme/codebase-rag:standard
docker pull royisme/codebase-rag:full

# 2. Documentation accessible
curl -I https://docs.vantagecraft.dev
# Should return: HTTP/2 200

# 3. Local deployment works
make docker-minimal
curl http://localhost:8000/api/v1/health
# Should return: {"status": "healthy"}
```

---

## 📊 Configuration Matrix

| Step | Required | Estimated Time | Difficulty |
|------|----------|----------------|------------|
| GitHub Secrets | ✅ Yes | 5 minutes | Easy |
| Enable Pages | ✅ Yes | 2 minutes | Easy |
| DNS Config | ✅ Yes | 10 minutes (+ propagation) | Medium |
| Local Testing | ⚪ Optional | 30 minutes | Medium |
| CI/CD Verify | ✅ Yes | 15 minutes (wait time) | Easy |
| MCP Submission | ✅ Yes | 20 minutes | Easy |

**Total Time**: ~1-2 hours (mostly waiting for DNS/CI)

---

## 🆘 Troubleshooting

### GitHub Actions Fails

**Error**: "Error: Cannot connect to Docker daemon"
**Solution**: This shouldn't happen in GitHub Actions (uses hosted runners)

**Error**: "denied: requested access to the resource is denied"
**Solution**: Check DOCKER_HUB_TOKEN secret is set correctly

### DNS Not Resolving

**Issue**: `docs.vantagecraft.dev` doesn't resolve
**Solution**:
1. Wait for DNS propagation (up to 48 hours)
2. Check DNS record is correct
3. Try `dig docs.vantagecraft.dev +trace` to debug

### Documentation Build Fails

**Error**: "mkdocs: command not found"
**Solution**: This shouldn't happen (GitHub Actions installs dependencies)

**Error**: "Theme 'material' not found"
**Solution**: Check `.github/workflows/docs-deploy.yml` installs `mkdocs-material`

### Docker Build Fails Locally

**Error**: "Cannot find Dockerfile"
**Solution**: Run from repository root directory

**Error**: "No such file or directory: pyproject.toml"
**Solution**: Ensure you're in the correct directory

---

## 📞 Support

If you encounter issues:

1. **Check Logs**:
   - GitHub Actions: View workflow run details
   - Docker Build: Check `docker build` output
   - DNS: Use `nslookup` or `dig`

2. **Documentation**:
   - `DOCKER_IMPLEMENTATION_SUMMARY.md`
   - `MCP_REGISTRY_SUBMISSION_SUMMARY.md`
   - `mcp-registry-submission/SUBMISSION_GUIDE.md`

3. **Ask for Help**:
   - GitHub Issues: https://github.com/royisme/codebase-rag/issues
   - Docker MCP Registry: https://github.com/docker/mcp-registry/issues

---

## ✅ Completion Checklist

Once all steps are done:

- [ ] GitHub secrets configured
- [ ] GitHub Pages enabled
- [ ] DNS configured and propagated
- [ ] CI/CD workflows passing
- [ ] Docker images on Docker Hub
- [ ] Documentation live at docs.vantagecraft.dev
- [ ] MCP Registry PR submitted

**Status**: Ready for production use! 🎉

---

## 🚀 What's Next?

After configuration is complete:

1. **Test End-to-End**:
   - Install from Docker Hub
   - Connect to Neo4j
   - Test MCP tools

2. **Announce**:
   - Update README with badges
   - Write blog post
   - Share on social media

3. **Monitor**:
   - Watch MCP Registry PR
   - Respond to user issues
   - Gather feedback

4. **Iterate**:
   - Add more documentation
   - Improve based on feedback
   - Plan next features
