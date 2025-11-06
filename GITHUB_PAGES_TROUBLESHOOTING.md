# GitHub Pages 部署诊断和配置指南

## 问题：编译成功但没有部署

### 原因分析

你的 `.github/workflows/docs-deploy.yml` 配置了：

```yaml
deploy:
  if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'
```

**这意味着**：
- ✅ 在 main 分支会部署
- ❌ 在 feature 分支只会 build，不会 deploy
- ❌ PR 只会 build，不会 deploy

### 当前状态检查

1. **查看你当前在哪个分支**
   ```bash
   git branch
   # 如果显示 claude/fix-docker-env-config-*，那就是在 feature 分支
   ```

2. **查看 GitHub Actions 运行记录**
   - 访问：https://github.com/royisme/codebase-rag/actions
   - 点击最近的 "Deploy Documentation" workflow
   - 检查是否有 "deploy" job
   - 如果只有 "build" job，说明条件不满足

## 解决方案

### 方案 1：合并到 main 分支（推荐）

```bash
# 1. 确保当前分支所有更改已提交
git status

# 2. 切换到 main 分支
git checkout main

# 3. 合并你的 feature 分支
git merge claude/fix-docker-env-config-011CUqY1Y431FvqPZW6YAEhT

# 4. 推送到远程
git push origin main

# 5. GitHub Actions 会自动触发，这次会执行 deploy job
```

**验证**：
- 访问 Actions 页面
- 应该看到 "build" 和 "deploy" 两个 job
- deploy job 完成后，会显示部署 URL

### 方案 2：手动触发 workflow

如果你还在 feature 分支，但想测试部署：

```bash
# 在 GitHub 网站上
1. 访问：https://github.com/royisme/codebase-rag/actions/workflows/docs-deploy.yml
2. 点击 "Run workflow" 按钮
3. 选择 "main" 分支
4. 点击 "Run workflow"
```

## GitHub Pages 设置配置

### 必须配置的设置

1. **访问仓库设置**
   ```
   https://github.com/royisme/codebase-rag/settings/pages
   ```

2. **Source 设置**
   - ✅ 选择 "GitHub Actions"
   - ❌ 不要选择 "Deploy from a branch"

   ![Source Setting](https://docs.github.com/assets/cb-49683/mw-1440/images/help/pages/publishing-source-drop-down.webp)

3. **Custom domain 设置**

   **需要配置！** 因为你有 `docs/CNAME` 文件：

   ```
   Custom domain: code-graph.vantagecraft.dev
   ☑ Enforce HTTPS
   ```

   **为什么需要？**
   - 你的 `docs/CNAME` 文件内容是 `code-graph.vantagecraft.dev`
   - 这告诉 GitHub Pages 你想使用自定义域名
   - 必须在 Settings 中也配置这个域名

### DNS 配置（必须）

在你的域名服务商（vantagecraft.dev）配置：

**CNAME 记录**：
```
类型: CNAME
名称: code-graph
目标: royisme.github.io
TTL: 3600 (或自动)
```

**如何验证**：
```bash
# 检查 DNS 是否生效
nslookup code-graph.vantagecraft.dev

# 或者
dig code-graph.vantagecraft.dev

# 应该显示：
# code-graph.vantagecraft.dev. IN CNAME royisme.github.io.
```

### 完整配置步骤

#### Step 1: 配置 DNS（在域名服务商）

```
记录类型: CNAME
主机记录: code-graph
记录值: royisme.github.io
TTL: 默认或3600
```

保存后等待 5-10 分钟生效。

#### Step 2: 配置 GitHub Pages

1. 访问：https://github.com/royisme/codebase-rag/settings/pages

2. **Source 设置**：
   - Source: GitHub Actions ✅

3. **Custom domain 设置**：
   - 输入：`code-graph.vantagecraft.dev`
   - 点击 Save
   - 等待 DNS 验证（可能需要几分钟）
   - 验证成功后，勾选 "Enforce HTTPS"

#### Step 3: 触发部署

```bash
# 方法 1: 合并到 main 分支（推荐）
git checkout main
git merge your-feature-branch
git push origin main

# 方法 2: 手动触发
# 在 GitHub Actions 页面点击 "Run workflow"

# 方法 3: 修改文档触发
echo "test" >> docs/index.md
git add docs/index.md
git commit -m "docs: trigger deployment"
git push origin main
```

#### Step 4: 验证部署

1. **查看 GitHub Actions**
   - https://github.com/royisme/codebase-rag/actions
   - 应该看到 "build" 和 "deploy" 两个 job
   - deploy job 状态应该是绿色 ✅

2. **查看 Pages 设置**
   - https://github.com/royisme/codebase-rag/settings/pages
   - 应该显示："Your site is live at https://code-graph.vantagecraft.dev"

3. **访问网站**
   - https://code-graph.vantagecraft.dev
   - 应该能看到文档

## 常见问题排查

### 问题 1: deploy job 不执行

**症状**：只有 build job，没有 deploy job

**原因**：
- 不在 main 分支
- 是 Pull Request

**解决**：
```bash
git checkout main
git push origin main
```

### 问题 2: DNS check failed

**症状**：GitHub Pages 显示 "DNS check unsuccessful"

**原因**：DNS 记录未生效或配置错误

**解决**：
```bash
# 1. 检查 DNS
dig code-graph.vantagecraft.dev

# 2. 确保返回 CNAME 记录指向 royisme.github.io
# 3. 等待 DNS 传播（5-60分钟）
# 4. 在 GitHub Pages 设置中点击 "Remove" 再重新添加域名
```

### 问题 3: 404 Not Found

**症状**：访问域名显示 404

**原因**：
- 部署未完成
- CNAME 文件缺失
- 域名配置不一致

**解决**：
```bash
# 1. 确认 docs/CNAME 文件存在
cat docs/CNAME
# 应该显示：code-graph.vantagecraft.dev

# 2. 确认 GitHub Pages 设置中的 Custom domain 与 CNAME 一致

# 3. 重新构建
git commit --allow-empty -m "chore: trigger rebuild"
git push origin main
```

### 问题 4: HTTPS 证书问题

**症状**："Certificate error" 或 "Not secure"

**原因**：GitHub 还在生成 HTTPS 证书

**解决**：
- 等待 1-24 小时
- GitHub 会自动从 Let's Encrypt 获取证书
- 在此期间可以用 HTTP 访问：http://code-graph.vantagecraft.dev

### 问题 5: 部署成功但内容是旧的

**症状**：网站内容没更新

**解决**：
```bash
# 清除浏览器缓存
# 或强制刷新：Ctrl+Shift+R (Windows/Linux) 或 Cmd+Shift+R (Mac)

# 或等待 CDN 缓存过期（通常 10 分钟）
```

## 最佳实践

### 1. 开发流程

```bash
# Feature 分支开发
git checkout -b feature/docs-update
# ... 修改文档 ...
git commit -m "docs: update guide"
git push origin feature/docs-update

# 创建 PR → 在 PR 中会 build（但不 deploy）
# 合并到 main → 自动 deploy

# 或者直接在 main 分支开发（小改动）
git checkout main
# ... 修改 ...
git commit -m "docs: fix typo"
git push origin main  # 自动触发 deploy
```

### 2. 快速测试部署

如果想快速看到部署效果：

```bash
# 1. 空提交触发部署
git commit --allow-empty -m "docs: trigger deployment"
git push origin main

# 2. 或修改任意文档
echo "" >> docs/index.md
git add docs/index.md
git commit -m "docs: trigger deployment"
git push origin main
```

### 3. 监控部署状态

```bash
# 使用 GitHub CLI
gh run list --workflow=docs-deploy.yml

# 查看最新运行
gh run view --log

# 或在浏览器中查看
open https://github.com/royisme/codebase-rag/actions
```

## 配置检查清单

使用这个清单确保所有配置正确：

- [ ] **DNS 配置**
  - [ ] CNAME 记录：code-graph → royisme.github.io
  - [ ] DNS 已生效（用 dig/nslookup 验证）

- [ ] **GitHub Pages 设置**
  - [ ] Source: GitHub Actions
  - [ ] Custom domain: code-graph.vantagecraft.dev
  - [ ] DNS check: ✅ (绿色对勾)
  - [ ] Enforce HTTPS: ☑ (勾选)

- [ ] **代码仓库**
  - [ ] docs/CNAME 文件存在，内容正确
  - [ ] .github/workflows/docs-deploy.yml 存在
  - [ ] 在 main 分支

- [ ] **GitHub Actions**
  - [ ] Workflow 权限正确（pages: write）
  - [ ] 最近一次运行包含 deploy job
  - [ ] deploy job 状态：✅ Success

- [ ] **访问验证**
  - [ ] https://code-graph.vantagecraft.dev 可访问
  - [ ] HTTPS 证书有效
  - [ ] 内容显示正确

## 需要帮助？

如果按照以上步骤仍有问题，请提供：

1. 当前分支名：`git branch`
2. GitHub Actions 运行日志截图
3. GitHub Pages 设置页面截图
4. DNS 查询结果：`dig code-graph.vantagecraft.dev`

我会帮你进一步诊断！
