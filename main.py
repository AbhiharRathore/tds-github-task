import os
from pathlib import Path
from typing import List

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="12-Factor Config Precedence Demo")

# Assignment page may be hosted on a different origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

def coerce(key: str, value):
    text = str(value).strip()
    normalized_key = key.lower()
    if normalized_key in ("port", "workers"):
        return int(text)
    if normalized_key == "debug":
        return text.lower() in ("true", "1", "yes", "on")
    return text

def apply_layer(config: dict, layer: dict):
    for raw_key, value in layer.items():
        if value is None:
            continue
        key = str(raw_key).lower()
        if key.startswith("app_"):
            key = key[4:]
        if key == "num_workers":
            key = "workers"
        config[key] = coerce(key, value)

@app.get("/effective-config")
def effective_config(set: List[str] = Query(default=[])):
    config = dict(DEFAULTS)

    # Layer 2: environment-specific YAML.
    env_name = os.environ.get("APP_ENV", "development")
    yaml_path = BASE_DIR / f"config.{env_name}.yaml"
    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as f:
            yaml_layer = yaml.safe_load(f) or {}
        apply_layer(config, yaml_layer)

    # Layer 3: .env file, parsed separately so OS env vars remain higher priority.
    env_file = dotenv_values(BASE_DIR / ".env")
    apply_layer(config, env_file)

    # Layer 4: actual process environment variables with APP_ prefix.
    os_layer = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("APP_") and value is not None
    }
    apply_layer(config, os_layer)

    # Highest priority: repeated ?set=key=value CLI-style query parameters.
    for item in set:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip().lower()
        if not key:
            continue
        if key.startswith("app_"):
            key = key[4:]
        if key == "num_workers":
            key = "workers"
        config[key] = coerce(key, value)

    # Never disclose the actual API key.
    config["api_key"] = "****"
    return config

@app.get("/")
def root():
    return {"service": "config-precedence", "endpoint": "/effective-config"}
