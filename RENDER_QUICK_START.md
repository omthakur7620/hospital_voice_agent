# 🚀 Render Deployment - Quick Start

## 3-Minute Setup

### Step 1: Push Code
```bash
cd D:\Codes\hospital_voice_agent
git add -A
git commit -m "Configure for Render deployment"
git push origin main
```

### Step 2: Create on Render

1. Go to https://render.com/dashboard
2. Click "New" → "Web Service"
3. Select GitHub repository
4. Choose `hospital_voice_agent`
5. Click "Connect"

### Step 3: Configure

- **Name:** `hospital-voice-api`
- **Root Directory:** `/` (default)
- **Runtime:** Select "Docker" (auto-detected)
- **Plan:** Starter (free)
- **Region:** Oregon
- **Branch:** main

### Step 4: Environment

Render will read from `render.yaml` automatically. You can also set manually:
- `APP_ENV=production`
- `DEBUG=false`
- `LOG_LEVEL=WARNING`

### Step 5: Add Database

1. Click "+" → "PostgreSQL"
2. Link to your web service
3. Click "Create"

### Step 6: Deploy

Click "Create Web Service" - it starts automatically!

Wait 3-5 minutes for deployment to complete.

---

## ✅ Test It

After deployment:

```bash
# Test health endpoint
curl https://your-app-name.onrender.com/health

# Should respond with:
# {"status":"healthy",...}
```

---

## 🎯 Done!

Your app is now live on Render! 🎉

- **App URL:** `https://your-app-name.onrender.com`
- **API Docs:** `https://your-app-name.onrender.com/docs` (if DEBUG=true)
- **Health Check:** `https://your-app-name.onrender.com/health`

---

## 📚 More Info

See `RENDER_DEPLOYMENT.md` for:
- Complete setup guide
- Custom domain setup
- Troubleshooting
- Performance optimization
- Security best practices

---

**Status:** ✅ Ready to deploy to Render

**Command:** Visit https://render.com and follow steps above!
