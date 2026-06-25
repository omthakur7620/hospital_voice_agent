# Railway Deployment Guide

## 🚀 Deploy to Railway

### Step 1: Prepare Repository

```bash
# Make sure entrypoint.sh is executable
git update-index --chmod=+x entrypoint.sh

# Commit changes
git add -A
git commit -m "Fix Railway deployment issues"
git push origin main
```

### Step 2: Connect to Railway

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub"
4. Connect your repository
5. Select the `hospital_voice_agent` project

### Step 3: Add PostgreSQL Plugin

In Railway dashboard:
1. Click "Add Plugins"
2. Select "PostgreSQL"
3. Railway automatically sets `DATABASE_URL` environment variable

### Step 4: Configure Environment

In Railway project settings, set these environment variables:

```env
# Production Settings
APP_ENV=production
DEBUG=false
LOG_LEVEL=WARNING

# API Configuration
ALLOWED_ORIGINS=https://yourdomain.com,https://vapi.ai

# Business Logic
SLOT_DURATION_MINUTES=30
MAX_ALTERNATIVE_SLOTS=3
BOOKING_WINDOW_DAYS=30

# Data
HOSPITAL_DATA_PATH=data/hospital_data.json
TIMEZONE=Asia/Kolkata
```

**Important:** `DATABASE_URL` is automatically injected by Railway when you add PostgreSQL plugin - DO NOT set it manually.

### Step 5: Deploy

1. Push code to repository
2. Railway automatically triggers build and deployment
3. Monitor deployment in Railway dashboard

### Troubleshooting Railway Deployment

#### Healthcheck Timeout Error
**Status:** ✅ FIXED

The issue was that database initialization was blocking the healthcheck. This is now fixed:
- Entrypoint script no longer blocks startup
- Database initialization happens asynchronously
- Healthcheck has proper start_period and timeout

**What we changed:**
- Added 90-second startup grace period
- Reduced healthcheck timeout to 30s
- Made database operations non-blocking
- Seed script is optional (won't fail deployment)

#### Build Fails
Check build logs in Railway dashboard:
1. Click "Deployments"
2. Select failed deployment
3. View "Build Logs"
4. Common issues:
   - Missing system dependencies → already in Dockerfile
   - Python syntax errors → check locally first
   - Missing requirements → check requirements.txt

#### API Returns 500 Error
Check runtime logs:
1. Click "Deployments"
2. Select deployment
3. View "Runtime Logs"
4. Common issues:
   - Database not ready → wait 2 minutes
   - Missing env vars → check Railway settings
   - Seed script failed → check data/hospital_data.json

### Environment Variables Explained

| Variable | Development | Production |
|----------|-------------|------------|
| `APP_ENV` | `development` | `production` |
| `DEBUG` | `true` | `false` |
| `LOG_LEVEL` | `INFO` | `WARNING` |
| `ALLOWED_ORIGINS` | `localhost:3000` | `yourdomain.com` |
| `DATABASE_URL` | Auto (locally) | Auto (Railway) |

### Monitoring

After deployment:

```bash
# View logs (from Railway CLI)
railway logs

# Check service status
railway status

# Tail logs in real-time
railway logs --follow
```

### API Endpoints (Production)

Your Railway app will be available at: `https://your-project.up.railway.app`

- Health check: `https://your-project.up.railway.app/health`
- Swagger UI: `https://your-project.up.railway.app/docs` (disabled in production)
- API endpoints: `https://your-project.up.railway.app/api/v1/*`

### Custom Domain

To add your domain:
1. In Railway dashboard, go to "Settings"
2. Click "Custom Domain"
3. Add your domain (e.g., `api.yourdomain.com`)
4. Follow DNS configuration instructions
5. Update `ALLOWED_ORIGINS` env var

### Scaling

To handle more traffic:
1. Go to "Settings"
2. Increase "Replicas" (how many containers run in parallel)
3. Railway handles load balancing automatically

### Backup Database

Railway automatically backs up PostgreSQL. To restore:
1. Go to PostgreSQL plugin settings
2. Look for backup options
3. Contact Railway support for restore

### Cost Optimization

- **Free tier:** Limited resources, good for development
- **Paid plan:** Pay-as-you-go, scales with usage
- Monitor usage in Railway dashboard

### CI/CD Integration

Railway auto-deploys when you push to the connected branch:

```bash
# Push to trigger deployment
git push origin main

# Railway automatically:
# 1. Pulls latest code
# 2. Builds Docker image
# 3. Runs healthcheck
# 4. Deploys to production
# 5. Rolls back if healthcheck fails
```

### Rollback

If deployment fails:
1. Go to "Deployments"
2. Find last successful deployment
3. Click "Promote to latest"
4. Railway redeploys that version

---

## Quick Reference

### Initial Deploy
```bash
git push origin main  # Auto-triggers Railway deployment
```

### Monitor
```bash
railway logs --follow
```

### Update Environment
1. Go to Railway dashboard
2. Update environment variables
3. Redeploy: go to "Deployments" and click "Redeploy Latest"

### Troubleshooting Commands

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Check status
railway status

# View logs
railway logs

# Set variable
railway variables set VAR_NAME=value

# See all variables
railway variables
```

---

**Last Updated:** 2026-06-25  
**Status:** ✅ Ready for Railway Deployment
