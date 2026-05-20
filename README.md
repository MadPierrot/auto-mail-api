# Auto Mail API

Proxy FastAPI per inoltrare le richieste di autoconfigurazione all'backend `automx2`.

## Installazione

1. Crea un ambiente virtuale Python:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```

## Configurazione

Crea un file `.env` a partire da `.env.example` e imposta l'URL di `automx2`:

```bash
cp .env.example .env
```

- `AUTOMX2_URL`: URL completo del backend automx2, ad esempio `http://localhost:9999`

## Avvio

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

- `GET /` - health check.
- `ANY /{path}` - inoltra qualsiasi richiesta verso l'URL configurato di `automx2` mantenendo metodo, query e corpo.

### Esempio

```bash
curl "http://localhost:8000/.well-known/autoconfig/mail/config-v1.1.xml?email=user@example.com"
```

Questo verrà inoltrato a `AUTOMX2_URL` preservando il percorso e i parametri di query.

## Docker

Costruisci l'immagine Docker con:

```bash
docker build -t auto-mail-api:latest .
```

E avvia il container con:

```bash
docker run -p 8000:8000 --env LOG_LEVEL=DEBUG auto-mail-api:latest
```

## GitHub Container Registry

La pipeline GitHub Actions `./github/workflows/docker-publish.yml` costruisce e pubblica l'immagine su `ghcr.io/${{ github.repository_owner }}/auto-mail-api` quando viene eseguito un push su `main`.

Se usi il repository GitHub, puoi scaricare l'immagine con:

```bash
docker pull ghcr.io/<owner>/auto-mail-api:latest
```
