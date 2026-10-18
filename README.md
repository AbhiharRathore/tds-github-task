# FastAPI Statistics API

This service calculates statistics from the integers supplied to `GET /stats`.
The allowed browser origin is `https://dash-78863e.example.com`.

## Run locally on Windows

From the project directory in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

In a second PowerShell terminal, send a request:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/stats?values=1,2,3"
```

The API returns the email, count, sum, minimum, maximum, and arithmetic mean.
Every response includes a unique `X-Request-ID` and a non-negative
`X-Process-Time` in seconds. Invalid or missing values return HTTP 422.

The interactive API docs are available at `http://127.0.0.1:8000/docs`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The tests cover dynamic statistics, input errors, response headers, CORS
preflight behavior, and the OpenAPI endpoint.

## Deploy to Render

The included `render.yaml` defines a free Render web service. To deploy:

1. Push this project to a GitHub repository. Do not publish local environment
   files, credentials, request recordings, or generated archives.
2. In Render, choose **New +** → **Blueprint**, connect the repository, and
   apply the `render.yaml` configuration.
3. Wait for the service to finish deploying. Render will show its public
   `https://...onrender.com` URL.
4. Verify the deployed endpoint, for example:

   ```powershell
   Invoke-RestMethod "https://YOUR-SERVICE.onrender.com/stats?values=1,2,3"
   ```

5. Submit the public URL with `/stats` appended to the assignment grader.

This workspace currently has no Git remote configured. The repository must be
connected to a remote before Render can deploy it from source control.
