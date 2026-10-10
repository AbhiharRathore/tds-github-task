# 12-Factor Config Precedence API

## Run locally (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
$env:APP_WORKERS = "1"
$env:APP_DEBUG = "true"
$env:APP_LOG_LEVEL = "warning"
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/effective-config`.

Try CLI-style overrides:
`http://127.0.0.1:8000/effective-config?set=port%3D9000&set=debug%3Dfalse`

## Deploy on Render

1. Push these files to a GitHub repository.
2. In Render, choose **New + → Blueprint** and connect the repository.
3. Render reads `render.yaml` and deploys the service.
4. Copy the public service URL and append `/effective-config`.
5. Test the endpoint with `?set=port%3D9000&set=debug%3Dfalse`.

The actual deployment URL can only be provided after the service is deployed in your hosting account.

## Deploy on Vercel

Vercel detects the FastAPI `app` in `main.py` and installs dependencies from
`requirements.txt`; no separate entry point or local service is required. Import
the existing GitHub repository as a Vercel project and deploy it. The checked-in
YAML file is loaded relative to `main.py`. Since `.env` files are not committed,
add any desired `.env`-layer values as Vercel environment variables for the
deployment environment. The `/effective-config` endpoint is then available at
the project URL.
