# Production Deployment

This guide covers deploying Code Graph Knowledge System to production, including documentation hosting on vantagecraft.dev.

## 📝 Documentation Deployment (vantagecraft.dev)

### Option 1: GitHub Pages (Recommended)

Deploy documentation automatically using GitHub Actions.

#### Prerequisites

- GitHub repository
- Domain `vantagecraft.dev` with DNS access

#### Step 1: Configure DNS

Add a CNAME record for your documentation subdomain:

```dns
Type: CNAME
Name: docs
Value: royisme.github.io
TTL: 3600
```

Or for root domain:

```dns
Type: A
Name: @
Value: 185.199.108.153
Value: 185.199.109.153
Value: 185.199.110.153
Value: 185.199.111.153
```

#### Step 2: Configure GitHub Pages

1. Create `docs/CNAME` file:

```bash
echo "docs.vantagecraft.dev" > docs/CNAME
```

2. Enable GitHub Pages in repository settings:
   - Go to Settings → Pages
   - Source: GitHub Actions

#### Step 3: Deploy

The GitHub Actions workflow will automatically deploy on push to main:

```bash
git add .
git commit -m "Add documentation"
git push origin main
```

Your documentation will be available at: **https://docs.vantagecraft.dev**

### Option 2: Self-Hosted (Nginx)

Host documentation on your own server.

#### Prerequisites

- Server with Nginx
- Domain configured
- SSL certificate (Let's Encrypt recommended)

#### Step 1: Build Documentation

```bash
# Install dependencies
pip install mkdocs-material mkdocs-minify-plugin mkdocs-git-revision-date-localized-plugin

# Build
mkdocs build

# Output in site/ directory
```

#### Step 2: Configure Nginx

```nginx
# /etc/nginx/sites-available/docs.vantagecraft.dev

server {
    listen 80;
    server_name docs.vantagecraft.dev;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name docs.vantagecraft.dev;

    ssl_certificate /etc/letsencrypt/live/docs.vantagecraft.dev/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/docs.vantagecraft.dev/privkey.pem;

    root /var/www/docs.vantagecraft.dev;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Cache static assets
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### Step 3: Deploy

```bash
# Copy built site to server
rsync -avz site/ user@server:/var/www/docs.vantagecraft.dev/

# Reload Nginx
ssh user@server 'sudo nginx -t && sudo systemctl reload nginx'
```

#### Step 4: SSL Certificate (Let's Encrypt)

```bash
# On server
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d docs.vantagecraft.dev

# Auto-renewal is configured automatically
```

### Option 3: Cloudflare Pages

Deploy to Cloudflare Pages for global CDN.

#### Step 1: Connect Repository

1. Go to Cloudflare Pages dashboard
2. Create new project from GitHub
3. Select your repository

#### Step 2: Configure Build

```yaml
Build command: mkdocs build
Build output directory: site
Root directory: /
```

#### Step 3: Custom Domain

1. Add custom domain: `docs.vantagecraft.dev`
2. Cloudflare will configure DNS automatically

---

## 🚀 Application Production Deployment

### Docker Swarm Deployment

For production workloads, use Docker Swarm or Kubernetes.

#### Single Node Setup

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.full.yml codebase-rag
```

#### Stack Configuration

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.15-enterprise
    deploy:
      replicas: 1
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    volumes:
      - neo4j_data:/data
    environment:
      - NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
      # ... other production configs

  mcp:
    image: royisme/codebase-rag:full
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
    environment:
      # Production environment variables
```

### Kubernetes Deployment

#### Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Helm 3+

#### Step 1: Create Namespace

```bash
kubectl create namespace codebase-rag
```

#### Step 2: Deploy Neo4j

```yaml
# neo4j-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: neo4j
  namespace: codebase-rag
spec:
  serviceName: neo4j
  replicas: 1
  selector:
    matchLabels:
      app: neo4j
  template:
    metadata:
      labels:
        app: neo4j
    spec:
      containers:
      - name: neo4j
        image: neo4j:5.15-community
        ports:
        - containerPort: 7474
          name: http
        - containerPort: 7687
          name: bolt
        env:
        - name: NEO4J_AUTH
          valueFrom:
            secretKeyRef:
              name: neo4j-auth
              key: auth
        volumeMounts:
        - name: data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
```

#### Step 3: Deploy Application

```yaml
# mcp-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-full
  namespace: codebase-rag
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-full
  template:
    metadata:
      labels:
        app: mcp-full
    spec:
      containers:
      - name: mcp-full
        image: royisme/codebase-rag:full
        ports:
        - containerPort: 8000
        env:
        - name: NEO4J_URI
          value: "bolt://neo4j:7687"
        - name: NEO4J_PASSWORD
          valueFrom:
            secretKeyRef:
              name: neo4j-auth
              key: password
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

#### Step 4: Create Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-full
  namespace: codebase-rag
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  selector:
    app: mcp-full
```

#### Step 5: Deploy

```bash
kubectl apply -f neo4j-deployment.yaml
kubectl apply -f mcp-deployment.yaml
kubectl apply -f service.yaml
```

---

## 🔒 Security Best Practices

### 1. Environment Variables

Never commit secrets to git:

```bash
# Use Kubernetes secrets
kubectl create secret generic app-secrets \
  --from-literal=neo4j-password=xxx \
  --from-literal=openai-api-key=xxx \
  -n codebase-rag
```

### 2. Network Security

```bash
# Restrict Neo4j access
# Only allow from application pods
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: neo4j-policy
spec:
  podSelector:
    matchLabels:
      app: neo4j
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: mcp-full
```

### 3. TLS/SSL

Use cert-manager for automatic certificate management:

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create issuer
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@vantagecraft.dev
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

### 4. Rate Limiting

```nginx
# Nginx ingress annotation
nginx.ingress.kubernetes.io/limit-rps: "10"
nginx.ingress.kubernetes.io/limit-connections: "5"
```

---

## 📊 Monitoring

### Prometheus Metrics

Application exposes metrics at `/metrics`:

```yaml
# prometheus-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: mcp-full
spec:
  selector:
    matchLabels:
      app: mcp-full
  endpoints:
  - port: http
    path: /metrics
```

### Logging

Use ELK stack or Loki for centralized logging:

```yaml
# fluent-bit configmap
[OUTPUT]
    Name es
    Match *
    Host elasticsearch
    Port 9200
    Index codebase-rag
```

---

## 🔄 Backup & Recovery

### Neo4j Backup

```bash
# Manual backup
docker exec codebase-rag-neo4j \
  neo4j-admin database dump neo4j \
  --to=/backups/neo4j-$(date +%Y%m%d).dump

# Automated backup (cron)
0 2 * * * /usr/local/bin/backup-neo4j.sh
```

### Restore

```bash
# Stop services
docker-compose down

# Restore backup
docker run --rm \
  -v neo4j_data:/data \
  -v $(pwd)/backups:/backups \
  neo4j:5.15 \
  neo4j-admin database load neo4j \
  --from=/backups/neo4j-20240101.dump

# Start services
docker-compose up -d
```

---

## 📚 Next Steps

- [Monitoring & Observability](monitoring.md)
- [Performance Tuning](performance.md)
- [Disaster Recovery](disaster-recovery.md)
- [Scaling Guide](scaling.md)
