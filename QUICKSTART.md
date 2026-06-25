# 🚀 Quick Start Guide

## 🐳 Docker Deployment (Recommended)

### Windows / macOS / Linux (Any OS)

```bash
# 1. Navigate to project
cd hospital_voice_agent

# 2. Start services
docker-compose up -d --build

# 3. Check status
docker-compose ps

# 4. View logs (if needed)
docker-compose logs -f api

# 5. Test API
curl http://localhost:8000/health
```

**API Documentation:** http://localhost:8000/docs

---

## 💻 Local Development

### Windows
```bash
# Simply run:
run-local.bat
```

### Linux / macOS
```bash
# Make executable and run:
chmod +x run-local.sh
./run-local.sh
```

---

## 🛑 Stop Services

```bash
# Stop but keep data
docker-compose stop

# Stop and remove containers (data persists)
docker-compose down

# Stop and remove everything including database
docker-compose down -v
```

---

## 🔧 Common Commands

```bash
# View all logs
docker-compose logs

# Follow logs (real-time)
docker-compose logs -f

# View specific service logs
docker-compose logs api
docker-compose logs postgres

# Connect to database
docker-compose exec postgres psql -U postgres -d hospital_voice

# Restart services
docker-compose restart

# Rebuild images (if code changed)
docker-compose up -d --build
```

---

## ✅ Verification

After startup, verify everything works:

```bash
# 1. Check services running
docker-compose ps
# Should show: postgres (healthy), api (healthy)

# 2. Test health endpoint
curl http://localhost:8000/health

# 3. Access Swagger docs
open http://localhost:8000/docs
# or
curl http://localhost:8000/docs
```

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8000 in use | Change port in `docker-compose.yml` or close app using it |
| Port 5432 in use | Change postgres port in `docker-compose.yml` |
| Database won't connect | Wait 30 seconds, check: `docker-compose logs postgres` |
| API won't start | Check logs: `docker-compose logs api` |
| Permission denied (entrypoint.sh) | Run: `chmod +x entrypoint.sh` |

---

## 📚 Documentation Files

- **DEPLOYMENT.md** - Full deployment guide
- **FIXES_SUMMARY.md** - What was fixed and why
- **README.md** - Project overview

---

**Ready to deploy!** ✅
