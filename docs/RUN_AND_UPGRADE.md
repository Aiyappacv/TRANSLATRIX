# Safe Docker Rebuild and Run Instructions

The Compose project defaults to `translatrix-pro`. It does not target the existing `translatrix-pro-intergrated` project.

Default host ports:

- Frontend: `8081`
- Backend: `8001`
- PostgreSQL and Redis are internal only.

## Replace the current `translatrix-pro` test stack

From the extracted project root:

```bash
copy .env.example .env
```

On Linux/macOS use:

```bash
cp .env.example .env
```

Review `.env`, then rebuild only this project:

```bash
docker compose -p translatrix-pro down
docker compose -p translatrix-pro up --build -d
```

This does not stop or remove `translatrix-pro-intergrated`.

Check status:

```bash
docker compose -p translatrix-pro ps
```

Open:

```text
Frontend: http://localhost:8081
Backend health: http://localhost:8001/health
Backend docs: http://localhost:8001/docs
```

## Preserve current data

`docker compose down` keeps named volumes. Do not add `-v` when existing test data must remain.

A full clean reset is destructive:

```bash
docker compose -p translatrix-pro down -v
```

## Use different ports

Change only these values in `.env`:

```text
FRONTEND_HOST_PORT=8082
BACKEND_HOST_PORT=8002
```

Then rebuild with the same project name.

## View logs

```bash
docker compose -p translatrix-pro logs -f backend
docker compose -p translatrix-pro logs -f frontend
```

## First verification after rebuild

1. Open `/health` and confirm the backend is healthy.
2. Open the frontend and sign in with a development account.
3. Upload a small text/PDF/image document.
4. Confirm the processing status completes and a financial entry/review task is created.
5. Test download, then refresh to confirm persistence.

Development credentials are in `docs/TEST_CREDENTIALS.md`.
