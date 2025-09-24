# 🚀 VPS Deployment Guide - EasyPanel

Complete guide to deploy Hyperliquid Funding Rate Scraper on VPS using EasyPanel.

## 📋 Prerequisites

- VPS with at least 1GB RAM and 1 CPU core
- EasyPanel installed on your VPS
- Docker and Docker Compose support
- Supabase account with database created

## 🔧 Quick Deployment Steps

### 1. **Prepare Your EasyPanel**

1. Access your EasyPanel dashboard
2. Go to **Projects** → **Create New Project**
3. Choose **Docker Compose** deployment method

### 2. **Upload Project Files**

Upload these files to your EasyPanel project:

```
├── Dockerfile
├── docker-compose.yml
├── easypanel.yml
├── requirements.txt
├── src/
├── migrations/
├── monitoring/
└── .env.production
```

### 3. **Configure Environment**

1. In EasyPanel, go to **Environment Variables**
2. Copy contents from `.env.production`
3. **IMPORTANT**: Update these values:

```env
# Replace with your actual Supabase credentials
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Optional: Customize timezone
TZ=America/Sao_Paulo

# Optional: Adjust scraping interval (minutes)
RUN_INTERVAL_MINUTES=10
```

### 4. **Deploy with EasyPanel**

```bash
# Option 1: Use EasyPanel interface
1. Click "Deploy" in EasyPanel dashboard
2. Select docker-compose.yml
3. Wait for build and deployment

# Option 2: Use command line (if SSH access)
git clone your-repo
cd hyperliquid-funding-scraper
chmod +x deploy.sh
./deploy.sh production
```

### 5. **Verify Deployment**

Access these URLs (replace with your domain):

- **Health Dashboard**: `http://your-domain.com:8080`
- **Health Check**: `http://your-domain.com:8080/health`
- **API Status**: `http://your-domain.com:8080/api/status`
- **Logs**: `http://your-domain.com:8080/logs/`
- **Data Exports**: `http://your-domain.com:8080/exports/`

## 🎛️ EasyPanel Configuration

### Resource Requirements

```yaml
# Minimum VPS specs
RAM: 1GB (2GB recommended)
CPU: 1 core (2 cores recommended)
Storage: 10GB (20GB recommended)
Bandwidth: Unlimited

# Container resources
CPU Limit: 1.5 cores
Memory Limit: 1.5GB
CPU Reservation: 0.5 cores
Memory Reservation: 512MB
```

### Port Configuration

```yaml
# Required ports in EasyPanel
8080: Health monitoring dashboard
3000: Grafana (optional, for monitoring profile)
9090: Prometheus (optional, for monitoring profile)
```

### Volume Mounts

```yaml
# Persistent data directories
./logs:/app/logs          # Application logs
./exports:/app/exports    # Data exports
./screenshots:/app/screenshots  # Debug screenshots
```

## ⚙️ Configuration Options

### Scraping Intervals

```env
# High frequency (every 10 minutes)
RUN_INTERVAL_MINUTES=10

# Standard (every 30 minutes)
RUN_INTERVAL_MINUTES=30

# Low frequency (every hour)
RUN_INTERVAL_MINUTES=60
```

### Performance Tuning

```env
# For low-resource VPS (512MB RAM)
MAX_WORKERS=1
BATCH_INSERT_SIZE=10
SCRAPING_TIMEOUT=60

# For standard VPS (1GB+ RAM)
MAX_WORKERS=3
BATCH_INSERT_SIZE=25
SCRAPING_TIMEOUT=45

# For high-performance VPS (2GB+ RAM)
MAX_WORKERS=5
BATCH_INSERT_SIZE=50
SCRAPING_TIMEOUT=30
```

## 📊 Monitoring & Health Checks

### Built-in Monitoring

The deployment includes:

1. **Health Dashboard** - Web interface showing status
2. **Health Check Endpoint** - `/health` for monitoring tools
3. **API Status** - `/api/status` for external monitoring
4. **Logs Access** - Web-based log viewing
5. **Data Export** - Download collected data

### Health Check Commands

```bash
# Check container health
curl http://your-domain:8080/health

# Get service status
curl http://your-domain:8080/api/status

# View recent logs
curl http://your-domain:8080/logs/

# Check container stats
docker stats hyperliquid-scraper
```

### Log Monitoring

```bash
# View live logs
docker-compose logs -f scraper

# View last 100 lines
docker-compose logs --tail=100 scraper

# Check for errors
docker-compose logs scraper | grep ERROR
```

## 🛠️ Maintenance Commands

### Service Management

```bash
# Restart scraper
docker-compose restart scraper

# Stop all services
docker-compose down

# Start with monitoring
docker-compose --profile monitoring up -d

# Update to latest code
git pull
docker-compose build --no-cache
docker-compose up -d
```

### Database Management

```bash
# Run database migrations
docker-compose exec scraper python migrations/migrate.py

# Test database connection
docker-compose exec scraper python -c "from src.database.supabase_client import SupabaseClient; SupabaseClient().test_connection()"

# Export data manually
docker-compose exec scraper python -m src.main --export-csv exports/manual_export.csv
```

### Troubleshooting

```bash
# Check container logs for errors
docker-compose logs scraper --tail=50

# Get shell access
docker-compose exec scraper /bin/bash

# Test Chrome/ChromeDriver
docker-compose exec scraper google-chrome --version
docker-compose exec scraper chromedriver --version

# Check disk space
docker system df

# Clean up unused resources
docker system prune -f
```

## 🔒 Security Considerations

### Firewall Rules

```bash
# Allow required ports
ufw allow 8080  # Health monitoring
ufw allow 22    # SSH access
ufw allow 80    # HTTP (if using reverse proxy)
ufw allow 443   # HTTPS (if using reverse proxy)
```

### Environment Security

- Store sensitive data in EasyPanel environment variables
- Use strong passwords for monitoring services
- Enable HTTPS with reverse proxy (nginx/Caddy)
- Regularly update container images
- Monitor logs for suspicious activity

## 📈 Scaling & Performance

### Horizontal Scaling

```yaml
# Scale scraper instances
docker-compose up -d --scale scraper=2

# Load balancer configuration (nginx)
upstream scrapers {
    server scraper_1:8080;
    server scraper_2:8080;
}
```

### Vertical Scaling

```yaml
# Increase resources in docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 3G
    reservations:
      cpus: '1.0'
      memory: 1G
```

## 💡 Tips for EasyPanel

1. **Use Environment Variables** - Store all config in EasyPanel environment
2. **Enable Auto-restart** - Set restart policy to `unless-stopped`
3. **Monitor Resource Usage** - Check CPU/RAM usage regularly
4. **Backup Data** - Regularly backup exports and logs
5. **Update Regularly** - Keep containers updated for security

## 🎯 Success Checklist

- [ ] EasyPanel project created
- [ ] Environment variables configured
- [ ] Supabase credentials added
- [ ] Deployment successful
- [ ] Health check returning 200 OK
- [ ] Logs showing successful data collection
- [ ] Data appearing in Supabase database
- [ ] Monitoring dashboard accessible

---

## 🆘 Support

If you encounter issues:

1. Check the health dashboard at `/health`
2. Review container logs: `docker-compose logs scraper`
3. Verify environment variables in EasyPanel
4. Test database connectivity manually
5. Check VPS resource usage (RAM/CPU)

Your Hyperliquid scraper should now be running 24/7, collecting funding rate data every 10 minutes! 🎉