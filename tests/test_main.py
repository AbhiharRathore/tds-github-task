import base64
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

import main


@pytest.fixture
def signing_key(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    monkeypatch.setattr(main, "IDP_PUBLIC_KEY", public_key)
    return private_key


@pytest.fixture
def client():
    return TestClient(main.app)


def make_token(private_key, *, audience=main.AUDIENCE, expires_at=None):
    now = int(time.time())
    claims = {
        "iss": main.ISSUER,
        "aud": audience,
        "exp": expires_at if expires_at is not None else now + 300,
        "sub": "student-123",
        "email": "student@example.com",
    }
    return jwt.encode(claims, private_key, algorithm="RS256")


def test_freshly_minted_valid_rs256_token_returns_claims(client, signing_key):
    token = make_token(signing_key)

    response = client.post("/verify", json={"token": token})

    assert response.status_code == 200
    assert response.json() == {
        "valid": True,
        "email": "student@example.com",
        "sub": "student-123",
        "aud": main.AUDIENCE,
    }


def test_expired_token_is_rejected(client, signing_key):
    token = make_token(signing_key, expires_at=int(time.time()) - 60)

    response = client.post("/verify", json={"token": token})

    assert response.status_code == 401
    assert response.json() == {"valid": False}


def test_wrong_audience_is_rejected(client, signing_key):
    token = make_token(signing_key, audience="another-audience")

    response = client.post("/verify", json={"token": token})

    assert response.status_code == 401
    assert response.json() == {"valid": False}


def test_wrong_issuer_is_rejected(client, signing_key):
    token = jwt.encode(
        {
            "iss": "https://other-idp.example",
            "aud": main.AUDIENCE,
            "exp": int(time.time()) + 300,
            "sub": "student-123",
            "email": "student@example.com",
        },
        signing_key,
        algorithm="RS256",
    )

    response = client.post("/verify", json={"token": token})

    assert response.status_code == 401
    assert response.json() == {"valid": False}


def test_tampered_payload_is_rejected(client, signing_key):
    token = make_token(signing_key)
    header, payload, signature = token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=="))
    claims["email"] = "attacker@example.com"
    tampered_payload = (
        base64.urlsafe_b64encode(
            json.dumps(claims, separators=(",", ":")).encode("utf-8")
        )
        .rstrip(b"=")
        .decode("ascii")
    )
    tampered_token = f"{header}.{tampered_payload}.{signature}"

    response = client.post("/verify", json={"token": tampered_token})

    assert response.status_code == 401
    assert response.json() == {"valid": False}


def test_token_signed_by_another_key_is_rejected(client):
    untrusted_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = make_token(untrusted_key)

    response = client.post("/verify", json={"token": token})

    assert response.status_code == 401
    assert response.json() == {"valid": False}


@pytest.mark.parametrize(
    "token",
    ["", "not-a-jwt", "a.b.c", "eyJhbGciOiJub25lIn0.e30."],
)
def test_malformed_or_non_rs256_tokens_are_rejected(client, token):
    response = client.post("/verify", json={"token": token})

    assert response.status_code == 401
    assert response.json() == {"valid": False}


@pytest.mark.parametrize("missing_claim", ["iss", "aud", "exp", "sub", "email"])
def test_missing_required_claim_is_rejected(client, signing_key, missing_claim):
    claims = {
        "iss": main.ISSUER,
        "aud": main.AUDIENCE,
        "exp": int(time.time()) + 300,
        "sub": "student-123",
        "email": "student@example.com",
    }
    claims.pop(missing_claim)
    token = jwt.encode(claims, signing_key, algorithm="RS256")

    response = client.post("/verify", json={"token": token})

    assert response.status_code == 401
    assert response.json() == {"valid": False}


def test_audience_array_is_returned_without_conversion(client, signing_key):
    audience = [main.AUDIENCE, "another-audience"]
    token = make_token(signing_key, audience=audience)

    response = client.post("/verify", json={"token": token})

    assert response.status_code == 200
    assert response.json()["aud"] == audience


def test_openapi_documents_verify_endpoint(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/verify" in response.json()["paths"]
