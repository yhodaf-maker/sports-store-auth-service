# ---- Build stage --------------------------------------------------------
FROM python:3.11.15-slim-bookworm@sha256:b18992999dbe963a45a8a4da40ac2b1975be1a776d939d098c647482bcad5cba AS build

WORKDIR /app

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

COPY requirements.txt .
# Package tooling is not needed after the virtual environment is assembled.
RUN python -m venv "${VIRTUAL_ENV}" \
    && pip install --no-cache-dir --requirement requirements.txt \
    && pip uninstall --yes setuptools wheel pip

# ---- Runtime stage --------------------------------------------------------
FROM python:3.11.15-slim-bookworm@sha256:b18992999dbe963a45a8a4da40ac2b1975be1a776d939d098c647482bcad5cba

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Remove base-image package tooling to reduce the runtime attack surface.
RUN python -m pip uninstall --yes setuptools wheel pip \
    && groupadd --gid 10001 auth \
    && useradd --uid 10001 --gid auth --no-create-home --shell /usr/sbin/nologin auth

WORKDIR /app

COPY --from=build /opt/venv /opt/venv
COPY --chown=auth:auth main.py cache.py database.py models.py security.py ./
COPY --chown=auth:auth routes ./routes

USER 10001

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3)"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
