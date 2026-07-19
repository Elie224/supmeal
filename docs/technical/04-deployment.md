# Guide de deploiement

## Prerequis

- Docker 20.10+ et Docker Compose v2+
- 2 Go de RAM minimum
- Ports 5432, 8765, 5173 disponibles

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

# 5. Lancer l application (inclut Mailpit de dev)
docker compose --profile dev up --build
```

L application est accessible sur :

- Client web : http://localhost:5173
- API : http://localhost:8765
- Documentation : http://localhost:8765/docs
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
| `SMTP_*` | Envoi des emails de verification | (obligatoire pour verification) |

### OAuth2

Pour activer un provider OAuth, creer une application sur la plateforme correspondante et renseigner les variables d environnement. Si un provider n est pas configure, ses routes renvoient 501.

Configuration locale recommandee:

- `APP_URL=http://localhost:5173`
- `GOOGLE_REDIRECT_URI=http://localhost:8765/api/v1/auth/oauth/google/callback`
- `GITHUB_REDIRECT_URI=http://localhost:8765/api/v1/auth/oauth/github/callback`

Valeurs a enregistrer chez les providers:

- Google Cloud Console
    - Authorized redirect URI: `http://localhost:8765/api/v1/auth/oauth/google/callback`
    - Authorized JavaScript origins: `http://localhost:5173`
- GitHub OAuth App
    - Authorization callback URL: `http://localhost:8765/api/v1/auth/oauth/github/callback`

Verification rapide:

- Ouvrir `GET /api/v1/auth/oauth/providers`.
- Les providers configures retournent `true` et apparaissent automatiquement dans l interface (connexion et parametres).

### SMTP (verification email)

Pour forcer la verification email avant acces a l interface, configurer un serveur SMTP:

- `SMTP_HOST` (ex: `smtp.mailgun.org`)
- `SMTP_PORT` (ex: `587`)
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_STARTTLS=true` (recommande avec port 587)
- `SMTP_USE_SSL=false` (mettre `true` si port SMTPS, ex 465)
- `SMTP_FROM_EMAIL` (ex: `no-reply@supmeal.app`)
- `SMTP_FROM_NAME` (ex: `SUPMEAL`)

Sans SMTP configure, la demande de code de verification renvoie `503`.

Configuration locale par defaut (deja pre-remplie dans `.env.example`):

- `SMTP_HOST=mailpit`
- `SMTP_PORT=1025`
- `SMTP_USE_STARTTLS=false`
- `SMTP_USE_SSL=false`
- `SMTP_FROM_EMAIL=no-reply@supmeal.local`

Mailpit est expose sur:

- SMTP: `localhost:1025`
- Interface web: `http://localhost:8025`

Procedure de verification locale:

1. Lancer les services: `docker compose --profile dev up -d --build`
2. Creer un compte (ou tenter un login sur un compte non verifie)
3. Ouvrir `http://localhost:8025`
4. Recuperer le code recu et le saisir dans l ecran "Verifier votre email"

Pour la production, remplacer ces valeurs par un vrai fournisseur SMTP (Brevo, Mailgun, SES, etc.) et activer TLS (`SMTP_USE_STARTTLS=true`, port 587 en general).

Configuration production recommandee (exemple Brevo):

- `SMTP_HOST=smtp-relay.brevo.com`
- `SMTP_PORT=587`
- `SMTP_USERNAME=<login Brevo SMTP>`
- `SMTP_PASSWORD=<cle SMTP Brevo>`
- `SMTP_USE_STARTTLS=true`
- `SMTP_USE_SSL=false`
- `SMTP_FROM_EMAIL=no-reply@supmeal.example.com`
- `SMTP_FROM_NAME=SUPMEAL`

Fichier modele production disponible: `.env.production.example`.

## Deploiement en production

### Variables de production

```bash
cp .env.production.example .env
```

Puis renseigner toutes les valeurs sensibles (secrets, mot de passe DB, credentials OAuth, credentials SMTP).

Demarrage sans Mailpit:

```bash
docker compose up -d --build
```

### Build optimise du frontend

```bash
cd frontend
npm install
npm run build
```

Le bundle statique est genere dans `frontend/dist/`. A servir par un reverse-proxy (Nginx, Caddy) ou directement par un serveur FastAPI separé.

### Reverse proxy Nginx (exemple)

```nginx
server {
    listen 80;
    server_name supmeal.example.com;

    location /api/ {
        proxy_pass http://localhost:8765/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        root /var/www/supmeal/frontend/dist;
        try_files $uri /index.html;
    }
}
```

### Changer `APP_ENV=production`

Cela desactive le reload automatique d uvicorn. Utiliser plutot :

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8765 --workers 4
```

### Volumes persistants

- `pgdata` : donnees PostgreSQL.
- `supmeal-uploads` : images uploadees (recettes, avatars).

Sauvegarder regulierement ces volumes.

## Maintenance

### Lancer les tests

```bash
docker compose run --rm backend python -m pytest -q
```

### Creer une nouvelle migration

```bash
docker compose exec backend alembic revision --autogenerate -m "ajout table X"
docker compose exec backend alembic upgrade head
```

### Acceder a la base de donnees

```bash
docker compose exec db psql -U supmeal -d supmeal
```

### Voir les logs

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

## Troubleshooting

- **Port deja utilise** : changer les ports dans `docker-compose.yml`.
- **Migrations echouees** : `docker compose down -v` puis `docker compose up --build` (ATTENTION : supprime les donnees).
- **WebSocket KO** : verifier que le reverse proxy supporte `Upgrade: websocket`.