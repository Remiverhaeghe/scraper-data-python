# Image du tableau de bord web et du planificateur, pour le NAS.
#
#   docker compose up -d
#
# Deux étapes : les dépendances sont compilées à part, l'image finale ne garde
# que l'environnement Python et le code, sans outil de compilation.

FROM python:3.14-slim AS dependances

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Versions et empreintes de toutes les dépendances : un paquet modifié sur PyPI
# fait échouer la construction au lieu de s'installer. Le fichier se régénère
# depuis requirements-server.txt, voir en tête de celui-ci.
COPY requirements-server.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements-server.lock


FROM python:3.14-slim

# Compte sans droits d'administration : le code ne peut modifier que data/ et
# logs/, montés depuis le NAS.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin jobboard

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JOBBOARD_DATA_DIR=/app/data \
    LOG_DIRECTORY=/app/logs

COPY --from=dependances /opt/venv /opt/venv

WORKDIR /app
COPY --chown=root:root config.py ./
COPY --chown=root:root job ./job
COPY --chown=root:root scheduler ./scheduler
COPY --chown=root:root scraper ./scraper
COPY --chown=root:root storage ./storage
COPY --chown=root:root utils ./utils
COPY --chown=root:root web ./web
COPY --chown=root:root assets ./assets
COPY --chown=root:root LICENSE ./

USER jobboard

EXPOSE 8000

HEALTHCHECK --interval=1m --timeout=10s --start-period=30s \
    CMD ["python", "-m", "web.healthcheck"]

CMD ["python", "-m", "web"]
