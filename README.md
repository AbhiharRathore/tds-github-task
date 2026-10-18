# JWT Verification API

This FastAPI service exposes `POST /verify`. It validates JSON Web Tokens
against the assignment's issuer, audience, RS256 algorithm, and supplied IdP
public key.

## Run locally on Windows

From the `jwt-verification-api` directory in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Example request:

```powershell
$body = @{ token = "YOUR_IDP_JWT" } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/verify `
  -Method Post -ContentType "application/json" -Body $body
```

A valid token returns HTTP 200 and its verified `email`, `sub`, and `aud`
claims. Any invalid token returns HTTP 401 with `{"valid":false}`. The service
requires `exp`, `iss`, `aud`, `sub`, and `email`; it never returns claims until
the signature and all registered claims have been verified.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The tests generate a temporary RSA key pair solely for local test tokens and
temporarily substitute its public key in the test process. The deployed
application always uses the assigned IdP public key in `main.py`; the test
private key is never stored or used by the service.

## Deploy to Render

The included `render.yaml` defines a free web service and uses Render's
`$PORT`. Push this project to a GitHub branch, then in Render select **New +**
→ **Blueprint**, connect the repository, select the deployment branch, and
apply the Blueprint. After deployment, the service URL shown in Render has
`/verify` appended for the assignment endpoint.

No private signing key or token is needed by the service. To test a successful
deployed verification, obtain a valid token signed by the assigned IdP; tokens
signed by the local test key are intentionally rejected by the deployed app.
