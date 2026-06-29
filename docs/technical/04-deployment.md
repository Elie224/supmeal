# Guide de deploiement

## Prerequis

- Docker 20.10+ et Docker Compose v2+
- 2 Go de RAM minimum
- Ports 5432, 8000, 5173 disponibles

## Demarrage rapide (developpement)

```bash
# 1. Cloner le projet
git clone <url> supmeal
cd supmeal

# 2. Copier le fichier d environnement
cp .env.example .env

# 3. (Optionnel) editer .env pour configurer OAuth2
# 4. Generer des secrets forts pour SECRET_KEY et JWT_SECRET :
python -c "import secrets; print(secrets.token_urlsafe(64))"

# 5. Lancer l application
docker compose up --build
```

L application est accessible sur :

- Client web : http://localhost:5173
- API : http://localhost:8000
- Documentation : http://localhost:8000/docs
- PostgreSQL : localhost:5432

Au premier lancement, les migrations Alembic sont executees automatiquement et la base est creee.

## Configuration

### Variables d environnement

| Variable | Description | Exemple |
|----------|-------------|---------|
| `APP_ENV` | development / production | development |
| `SECRET_KEY` | Cle secrete pour hash (>= 32 chars) | (64 chars random) |
| `JWT_SECRET` | Cle de signature JWT | (64 chars random) |
| `POSTGRES_*` | Connexion DB | (voir .env.example) |
| `GOOGLE_CLIENT_ID/SECRET` | OAuth Google | (optionnel) |
| `GITHUB_CLIENT_ID/SECRET` | OAuth GitHub | (optionnel) |
| `MICROSOFT_CLIENT_ID/SECRET` | OAuth Microsoft | (optionnel) |

### OAuth2

Pour activer un provider OAuth, creer une application sur la plateforme correspondante et renseigner les variables d environnement. Si un provider n est pas configure, ses routes renvoient 501.

## Deploiement en production

### Build optimise du frontend

```bash
cd web
npm install
npm run build
```

Le bundle statique est genere dans `web/dist/`. A servir par un reverse-proxy (Nginx, Caddy) ou directement par un serveur FastAPI separé.

### Reverse proxy Nginx (exemple)

```nginx
server {
    listen 80;
    server_name supmeal.example.com;

    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        root /var/www/supmeal/web/dist;
        try_files $uri /index.html;
    }
}
```

### Changer `APP_ENV=production`

Cela desactive le reload automatique d uvicorn. Utiliser plutot :

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Volumes persistants

- `pgdata` : donnees PostgreSQL.
- `supmeal-uploads` : images uploadees (recettes, avatars).

Sauvegarder regulierement ces volumes.

## Maintenance

### Lancer les tests

```bash
cd server
pip install -e ".[dev]"
pytest
```

### Creer une nouvelle migration

```bash
docker compose exec server alembic revision --autogenerate -m "ajout table X"
docker compose exec server alembic upgrade head
```

### Acceder a la base de donnees

```bash
docker compose exec db psql -U supmeal -d supmeal
```

### Voir les logs

```bash
docker compose logs -f server
docker compose logs -f web
docker compose logs -f db
```

## Troubleshooting

- **Port deja utilise** : changer les ports dans `docker-compose.yml`.
- **Migrations echouees** : `docker compose down -v` puis `docker compose up --build` (ATTENTION : supprime les donnees).
- **WebSocket KO** : verifier que le reverse proxy supporte `Upgrade: websocket`.