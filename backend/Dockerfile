FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependances systeme pour compiler et PIL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installation des dependances (cache optimise)
COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "sqlalchemy[asyncio]>=2.0.30" \
    "asyncpg>=0.29.0" \
    "alembic>=1.13.0" \
    "pydantic>=2.7.0" \
    "pydantic-settings>=2.4.0" \
    "python-multipart>=0.0.9" \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" \
    "bcrypt==4.0.1" \
    "authlib>=1.3.2" \
    "itsdangerous>=2.2.0" \
    "httpx>=0.27.0" \
    "email-validator>=2.1.0" \
    "aiofiles>=24.1.0" \
    "websockets>=12.0" \
    "pillow>=10.4.0" \
    "python-slugify>=8.0.0" \
    "tenacity>=9.0.0" \
    "pytest>=8.2.0" \
    "pytest-asyncio>=0.23.0" \
    "pytest-cov>=5.0.0"

# Code source
COPY . .

# Dossier d'uploads
RUN mkdir -p /app/uploads

EXPOSE 8000

# Demarrage : migrations puis uvicorn
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
