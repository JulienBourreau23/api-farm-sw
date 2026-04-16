# SW Farming — API Python (FastAPI)

## Installation sur le LXC

```bash
# 1. Prérequis
apt update && apt install -y python3.12 python3.12-venv python3-pip

# 2. Cloner / copier le projet
cd /opt
mkdir sw-api && cd sw-api

# 3. Environnement virtuel
python3.12 -m venv venv
source venv/bin/activate

# 4. Dépendances
pip install -r requirements.txt

# 5. Configuration
cp .env.example .env
# Éditer .env avec les vraies valeurs
nano .env

# 6. Lancer en dev
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 7. Lancer en prod (avec systemd)
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 2
```

## Service systemd (prod)

Créer `/etc/systemd/system/sw-api.service` :

```ini
[Unit]
Description=SW Farming FastAPI
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/sw-api
ExecStart=/opt/sw-api/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 2
Restart=always
EnvironmentFile=/opt/sw-api/.env

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable sw-api
systemctl start sw-api
```

## Endpoints

| Méthode | URL | Description |
|---------|-----|-------------|
| GET  | /health | Healthcheck |
| POST | /import/{user_id} | Upload JSON SW |
| GET  | /averages/{user_id}/{import_id} | Moyennes substats |

### Paramètres /averages

- `set_id` : ID du set (ex: 13 = Violent), null = tous
- `slot_no` : 1-6, null = tous
- `pri_stat` : ID stat principale (filtre slots 2/4/6)
- `min_upgrade` : niveau minimum (0-15)
- `refresh` : true pour forcer le recalcul du cache

## Documentation interactive

http://localhost:8001/docs
```
# api-farm-sw
