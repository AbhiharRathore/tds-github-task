import logging
import os
from pathlib import Path
from collections.abc import Mapping

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)

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

CONFIG_KEYS = {"port", "workers", "debug", "log_level", "api_key"}


def normalize_key(raw_key: object) -> str | None:
    key = str(raw_key).strip().lower()
    if key == "app_env":
        return None
    if key.startswith("app_"):
        key = key[4:]
    if key == "num_workers":
        return "workers"
    return key


def coerce(key: str, value: object) -> object:
    text = str(value).strip()
    if key in ("port", "workers"):
        return int(text)
    if key == "debug":
        return text.lower() in ("true", "1", "yes", "on")
    return text


def apply_layer(
    config: dict[str, object],
    layer: Mapping[str, object],
    *,
    source: str,
) -> None:
    for raw_key, value in layer.items():
        if value is None:
            continue
        key = normalize_key(raw_key)
        if key is None or not key:
            continue
        try:
            config[key] = coerce(key, value)
        except (TypeError, ValueError):
            logger.warning("Ignoring invalid %s value for configuration key %s", source, key)


def load_dotenv_config(path: Path) -> Mapping[str, object]:
    try:
        return dotenv_values(path)
    except (OSError, UnicodeError) as exc:
        logger.warning(
            "Unable to load environment file %s (%s); using lower-priority settings",
            path.name,
            type(exc).__name__,
        )
        return {}


def load_yaml_config(path: Path) -> Mapping[str, object]:
    try:
        with path.open("r", encoding="utf-8") as config_file:
            yaml_layer = yaml.safe_load(config_file)
    except FileNotFoundError:
        logger.info("Configuration file %s is missing; using lower-priority settings", path.name)
        return {}
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        logger.warning(
            "Unable to load configuration file %s (%s); using lower-priority settings",
            path.name,
            type(exc).__name__,
        )
        return {}

    if yaml_layer is None:
        return {}
    if not isinstance(yaml_layer, Mapping):
        logger.warning("Configuration file %s must contain a mapping; ignoring it", path.name)
        return {}
    return yaml_layer


@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    config = dict(DEFAULTS)

    # Layer 2: environment-specific YAML.
    env_name = os.environ.get("APP_ENV", "development")
    yaml_path = BASE_DIR / f"config.{env_name}.yaml"
    apply_layer(config, load_yaml_config(yaml_path), source="YAML")

    # Layer 3: .env file, parsed separately so OS env vars remain higher priority.
    env_file = load_dotenv_config(BASE_DIR / ".env")
    apply_layer(config, env_file, source=".env")

    # Layer 4: process environment variables with APP_ prefix or the worker alias.
    os_layer = {
        key: value
        for key, value in os.environ.items()
        if (
            (key.upper().startswith("APP_") and key.upper() != "APP_ENV")
            or key.upper() == "NUM_WORKERS"
        )
        and value is not None
    }
    apply_layer(config, os_layer, source="environment")

    # Highest priority: repeated ?set=key=value CLI-style query parameters.
    for item in set:
        if "=" not in item:
            raise HTTPException(
                status_code=400,
                detail="Invalid query override: expected key=value",
            )
        key, value = item.split("=", 1)
        normalized_key = normalize_key(key)
        if normalized_key not in CONFIG_KEYS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid configuration key '{key.strip()}'",
            )
        try:
            config[normalized_key] = coerce(normalized_key, value)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid integer for configuration key '{normalized_key}'",
            ) from None

    # Never disclose the actual API key.
    config["api_key"] = "****"
    return config

@app.get("/")
def root():
    return {"service": "config-precedence", "endpoint": "/effective-config"}
