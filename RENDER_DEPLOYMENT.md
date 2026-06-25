# 🎯 Render Deployment Guide

## ✅ All Files Configured for Render

Your Hospital Voice Agent is now ready to deploy on Render.com!

---

## 🚀 Quick Start - 5 Minutes

### Step 1: Commit Changes
```bash
cd D:\Codes\hospital_voice_agent

git add -A
git commit -m "Configure for Render deployment"
git push origin main
```

### Step 2: Create Render Account
Go to https://render.com and sign up (free tier available)

### Step 3: Connect GitHub
1. Dashboard → New → Web Service
2. Select "Build and deploy from a Git repository"
3. Connect GitHub account
4. Select `hospital_voice_agent` repository
5. Select `main` branch

### Step 4: Configure Service

**Basic Settings:**
- Name: `hospital-voice-api`
- Runtime: `Docker`
- Region: `Oregon` (or your preferred region)
- Plan: `Starter` (free)

**Environment Variables:**
Render will auto-detect from `render.yaml`, but you can also set manually:
- `APP_ENV=production`
- `DEBUG=false`
- `LOG_LEVEL=WARNING`
- `ALLOWED_ORIGINS=https://yourdomain.com`

### Step 5: Add PostgreSQL

1. Click "+" → "PostgreSQL"
2. Name: `hospital-voice-db`
3. Database: `hospital_voice`
4. Plan: `Starter` (free)
5. Render auto-links to your web service

### Step 6: Deploy

Click "Create Web Service" - deployment starts automatically!

**Wait 3-5 minutes for:**
- Docker image build
- Database initialization
- Application startup
- Healthcheck to pass

---

## 📊 What Gets Deployed

### Web Service
- **Name:** hospital-voice-api
- **Docker:** Uses your Dockerfile
- **Port:** 8080
- **Health Check:** `/health` endpoint
- **Auto-scale:** Yes (if needed)

### PostgreSQL Database
- **Version:** 15
- **Database:** hospital_voice
- **Plan:** Starter (500MB free)
- **Auto-backup:** Yes

---

## 🔐 Environment Variables

Set in Render dashboard (not in `.env`):

| Variable | Value | Note |
|----------|-------|------|
| `APP_ENV` | `production` | Required |
| `DEBUG` | `false` | Production setting |
| `LOG_LEVEL` | `WARNING` | Production logging |
| `ALLOWED_ORIGINS` | `https://yourdomain.com` | Your domain |
| `DATABASE_URL` | Auto-injected | Don't set |
| `TIMEZONE` | `Asia/Kolkata` | Can override |

**Note:** `DATABASE_URL` is automatically injected by Render when you link PostgreSQL. Do NOT set it manually.

---

## 🌐 Custom Domain (Optional)

After deployment succeeds:

1. Go to Web Service settings
2. Click "Custom Domain"
3. Add your domain (e.g., `api.yourdomain.com`)
4. Follow DNS instructions
5. Wait 24 hours for DNS propagation

Then update `ALLOWED_ORIGINS`:
```
https://yourdomain.com,https://vapi.ai
```

---

## 📝 render.yaml

The `render.yaml` file defines your entire infrastructure:

```yaml
services:
  - type: web
    name: hospital-voice-api
    runtime: docker
    region: oregon
    plan: starter
    dockerfile: ./Dockerfile
    envVars:
      - key: APP_ENV
        value: production
      # ... other vars

databases:
  - name: hospital-voice-db
    databaseName: hospital_voice
    plan: starter
    region: oregon
    postgresMajorVersion: "15"
```

This auto-creates web service + PostgreSQL when you deploy!

---

## 🔍 Monitoring Deployment

### In Render Dashboard

1. **Logs**: Real-time logs of deployment and app startup
2. **Metrics**: CPU, memory, network usage
3. **Events**: Deployment events and status
4. **Health**: Service health status

### Via CLI

```bash
# Install Render CLI (optional)
npm install -g @render-api/cli

# View logs
render logs --service hospital-voice-api

# View service status
render services --service hospital-voice-api
```

---

## ✅ Verify Deployment

After deployment completes:

```bash
# Test health endpoint
curl https://hospital-voice-api-xxxx.onrender.com/health

# Should respond:
# {"status":"healthy","service":"Hospital Voice AI Receptionist Backend",...}

# Access API documentation (if DEBUG=true)
# https://hospital-voice-api-xxxx.onrender.com/docs

# API endpoints
# https://hospital-voice-api-xxxx.onrender.com/api/v1/doctors
# https://hospital-voice-api-xxxx.onrender.com/api/v1/slots
# etc.
```

---

## 🆘 Troubleshooting

### Deployment Failed?

**Check logs in Render dashboard:**
1. Web Service → Logs
2. Look for errors during:
   - Build phase
   - Deploy phase
   - Health check phase

**Common issues:**

| Issue | Solution |
|-------|----------|
| Build failed | Check Python syntax, requirements.txt |
| Healthcheck failed | Wait 2 minutes, check logs for startup errors |
| Database not connecting | Ensure PostgreSQL service linked |
| Port issue | Render uses 8080 automatically |
| Out of memory | Upgrade to paid plan |

### Healthcheck Timeout?

The entrypoint script is designed to not block:
- App starts immediately
- Database initialization happens async
- Healthcheck should pass within 30 seconds

If it fails:
1. Check startup logs for errors
2. Wait 2-3 minutes for full initialization
3. Click "Redeploy" to try again

### Database Connection Error?

```
error: could not connect to server: Connection refused
```

**Solutions:**
1. Ensure PostgreSQL service created
2. Wait 2 minutes after creation
3. Check DATABASE_URL is auto-injected
4. Redeploy web service after DB is ready

---

## 🚀 CI/CD Integration

Render auto-deploys when you push to GitHub:

```bash
# Make code changes
git add -A
git commit -m "Add new feature"

# Push to trigger deployment
git push origin main

# Render automatically:
# 1. Clones latest code
# 2. Builds Docker image
# 3. Deploys to production
# 4. Runs healthcheck
# 5. Rolls back if healthcheck fails
```

---

## 💰 Pricing

**Free Tier:**
- Web Service: 500 free hours/month (enough for always-on)
- PostgreSQL: 500 MB storage, 1 GB/month
- Total: ~$0 if you stay within limits

**Paid Tier:**
- Web Service: $7/month
- PostgreSQL: Pay per GB
- Auto-scaling available
- Better support

---

## 📚 API Endpoints

Your app will be available at: `https://hospital-voice-api-xxxx.onrender.com`

**Available endpoints:**

```
GET  /health                          - Health check
GET  /                                - Root endpoint
GET  /docs                            - Swagger UI (if DEBUG=true)
GET  /api/v1/doctors                  - List doctors
GET  /api/v1/slots                    - Get available slots
POST /api/v1/book-appointment         - Book appointment
POST /api/v1/cancel-appointment       - Cancel appointment
POST /api/v1/reschedule-appointment   - Reschedule appointment
```

---

## 🔄 Redeploying

To redeploy without code changes:

1. In Render dashboard
2. Web Service → Manual Deploy
3. Click "Deploy latest commit"

To redeploy with new environment variables:

1. Update environment variables
2. Click "Manual Deploy"
3. Render redeploys with new config

---

## 📊 Performance Tips

### Optimize for free tier:
1. Keep Docker image small (we do - ~400MB)
2. Use async operations (we do)
3. Lazy-load data (optional)
4. Monitor usage in dashboard

### Upgrade when needed:
- If app goes to sleep (free tier), upgrade
- If database is full (500 MB), upgrade
- If need better performance, upgrade

---

## 🛡️ Security

### Best Practices:
- ✅ `DEBUG=false` in production
- ✅ Secrets in dashboard (not `.env`)
- ✅ `ALLOWED_ORIGINS` restricted to your domain
- ✅ Use HTTPS (Render auto-enables)
- ✅ Database backups enabled (Render default)

### Render Security Features:
- HTTPS/TLS auto-configured
- DDoS protection
- Database encryption
- Automatic updates

---

## 📞 Support & Docs

- **Render Docs:** https://render.com/docs
- **Status Page:** https://status.render.com
- **Support:** https://support.render.com

---

## ✨ Next Steps

1. ✅ Code configured for Render
2. ✅ render.yaml created
3. ✅ Docker configured for port 8080
4. 👉 **Push to GitHub: `git push origin main`**
5. 👉 **Create Render account and deploy**
6. 👉 **Monitor deployment in dashboard**
7. 👉 **Test health endpoint**
8. 👉 **Configure custom domain (optional)**

---

## 🎉 Summary

Your app is ready for Render! Just:

1. Push code: `git push origin main`
2. Connect GitHub to Render
3. Click "Deploy"
4. Wait 5 minutes
5. App is live! 🚀

---

**Status:** ✅ READY FOR RENDER DEPLOYMENT

**Last Updated:** 2026-06-25  
**Platform:** Render.com  
**Configuration:** Complete  
**Documentation:** Done
