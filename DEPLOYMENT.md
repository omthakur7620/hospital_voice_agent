# Hospital Voice Agent - Docker Deployment Guide

## 🎯 Overview

This document explains the Docker deployment setup for the Hospital Voice Agent backend API.

## ✅ All Fixes Applied

### 1. **Docker Compose Configuration** ✓
- ✅ Added missing PostgreSQL service definition
- ✅ Configured network bridge (`hospital-network`)
- ✅ Added volume management for persistent data
- ✅ Added health checks for both services
- ✅ Proper service dependency ordering

### 2. **Python Application** ✓
- ✅ Fixed import statements (moved from bottom to top of `app/main.py`)
- ✅ Fixed UTC timezone reference (`datetime.UTC` → `timezone.utc`)
- ✅ Proper error handling and logging

### 3. **Database Configuration** ✓
- ✅ Updated `.env` for Docker environment
- ✅ Fixed database connection string (localhost → postgres)
- ✅ Proper PostgreSQL credentials

### 4. **Docker Setup** ✓
- ✅ Enhanced Dockerfile with system dependencies
- ✅ Added curl for health checks
- ✅ Created entrypoint script for database initialization
- ✅ Added `.dockerignore` for optimized builds

### 5. **Development Scripts** ✓
- ✅ Created `run-local.sh` for Linux/macOS
- ✅ Created `run-local.bat` for Windows

---

## 🚀 Quick Start - Docker Deployment

### Prerequisites
- Docker and Docker Compose installed
- At least 2GB free disk space
- Port 8000 and 5432 available

### Step 1: Build and Start Services

```bash
# Navigate to project directory
cd /path/to/hospital_voice_agent

# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### Step 2: Verify Services

```bash
# Check service status
docker-compose ps

# View API logs
docker-compose logs -f api

# View database logs
docker-compose logs -f postgres
```

### Step 3: Test the API

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

---

## 🏠 Local Development Setup

### macOS / Linux

```bash
# Make the startup script executable
chmod +x run-local.sh

# Run the script (installs deps, initializes DB, starts app)
./run-local.sh
```

### Windows

```bash
# Simply run the batch file
run-local.bat
```

---

## 🔧 Manual Docker Commands

### Build Image
```bash
docker build -t hospital-voice-api:latest .
```

### Run Container
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/hospital_voice \
  hospital-voice-api:latest
```

### Stop Services
```bash
docker-compose down
```

### Remove Everything (including database)
```bash
docker-compose down -v
```

---

## 📁 Key Files Modified

### Configuration Files
- **`docker-compose.yml`** - Complete compose config with PostgreSQL
- **`.env`** - Docker-compatible environment variables
- **`.dockerignore`** - Optimized Docker build context

### Application Code
- **`app/main.py`** - Fixed imports and UTC reference
- **`Dockerfile`** - Enhanced with health checks

### Startup Scripts
- **`entrypoint.sh`** - Docker container initialization
- **`run-local.bat`** - Windows development startup
- **`run-local.sh`** - Linux/macOS development startup

---

## 🔒 Environment Variables

### Development (Docker)
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/hospital_voice
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000,https://vapi.ai
TIMEZONE=Asia/Kolkata
```

### Production
Update `.env` before deployment:
```env
DATABASE_URL=postgresql+asyncpg://produser:prodpass@prod-host:5432/hospital_voice
APP_ENV=production
DEBUG=false
LOG_LEVEL=WARNING
ALLOWED_ORIGINS=https://yourdomain.com
```

---

## 📊 Database Management

### Initialize Database
Database tables are created automatically on first run via the entrypoint script.

### Seed Data
Hospital data from `data/hospital_data.json` is automatically loaded.

### Direct Database Access
```bash
# Connect to PostgreSQL inside container
docker-compose exec postgres psql -U postgres -d hospital_voice

# View tables
\dt

# Exit
\q
```

---

## 🐛 Troubleshooting

### Error: "undefined network hospital-network"
**Status:** ✅ FIXED  
The network is now properly defined in `docker-compose.yml`

### Error: "Database connection failed"
**Solution:** 
1. Check PostgreSQL is running: `docker-compose ps`
2. Wait 10-30 seconds for database to be ready
3. Check logs: `docker-compose logs postgres`

### Error: "Connection refused on localhost:8000"
**Solution:**
1. Verify API container is running: `docker-compose ps api`
2. Check health: `docker-compose logs api`
3. Ensure port 8000 is not in use: `lsof -i :8000`

### Ports Already in Use
Change ports in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Use 8001 instead of 8000
```

### Python Import Errors
**Status:** ✅ FIXED  
All imports have been moved to the top of files and corrected.

---

## ✨ Deployment to Cloud

### Railway.app
```bash
# Push to Railway
railway up
```

### Heroku
```bash
# Build and deploy
heroku container:push web
heroku container:release web
```

### DigitalOcean / AWS / Azure
See `railway.json` for deployment configuration template.

---

## 🔍 API Endpoints

- `GET /health` - Health check
- `GET /` - Root endpoint
- `GET /docs` - Swagger UI (development only)
- `GET /api/v1/doctors` - List doctors
- `GET /api/v1/slots` - Get available slots
- `POST /api/v1/book-appointment` - Book appointment
- `POST /api/v1/cancel-appointment` - Cancel appointment
- `POST /api/v1/reschedule-appointment` - Reschedule appointment

---

## 📝 Notes

- All secrets should be managed via environment variables
- Database credentials in `.env` should be changed in production
- Logs are stored in `./logs/` directory (mounted volume in Docker)
- Automatic database migration happens on startup
- Health checks prevent requests to unhealthy services

---

## ✅ Validation Checklist

Before deployment, verify:

- [ ] Docker and Docker Compose are installed
- [ ] `docker-compose.yml` syntax is valid
- [ ] `.env` file contains correct credentials
- [ ] `entrypoint.sh` has execute permissions
- [ ] `data/hospital_data.json` exists and is valid
- [ ] Port 8000 and 5432 are available
- [ ] Firewall allows Docker container communication

---

## 📞 Support

For issues or questions:
1. Check Docker logs: `docker-compose logs`
2. Review `.env` configuration
3. Verify database connectivity
4. Check Python syntax: `python -m py_compile app/*.py`

---

**Last Updated:** 2026-06-25  
**Status:** ✅ Ready for Deployment
