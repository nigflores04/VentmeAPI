# Ventics AI API (FastAPI)

Minimal FastAPI service with a stub GenAI image generation endpoint, structured to be swapped with a real provider later.

## Features
- FastAPI app with versioned routes under `/v1`
- Health check at `/healthz`
- Image generation endpoint: `POST /v1/images/generate`
- Config via environment variables using pydantic-settings

## Install
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Run
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open Swagger UI at: http://localhost:8000/docs

## Endpoint Summary
- GET `/healthz` → `{ "status": "ok" }`
- POST `/v1/images/generate`
  - Request body:
    ```json
    {
      "prompt": "string",
      "width": 512,
      "height": 512,
      "seed": 123
    }
    ```
  - Response body:
    ```json
    {
      "image_base64": "...",
      "width": 512,
      "height": 512,
      "model": "stub"
    }
    ```

## Configuration
Configure via environment variables (optional):
- `APP_NAME` (default: "Ventics AI API")
- `VERSION` (default: "0.1.0")
- `MODEL_PROVIDER` (default: "stub")
- `TIMEOUT` (default: 30)

Create a `.env` file if you want to override defaults.
