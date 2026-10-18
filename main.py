from typing import Literal

import jwt
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

ISSUER = "https://idp.exam.local"
AUDIENCE = "tds-9ao2y9x5.apps.exam.local"
ALGORITHM = "RS256"
IDP_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
cxiP/hG8C6Sb9iwg3yiLAA4HCnpITcbWCSelbvbYGuc3EbNy4xFyf5Cbj5DHJMID
EkryOgyd2giIIIBOUBj8S63uGcnRpOBh9NFatfNwheKuzsPuVNldu6A9cNteNpXc
WyJjG2axVfmq7i6SuKr1JoWYG7xTTAvKPujSl4OtsQfO3h5NepzdfXpr28oNnzfW
ed+zclR6BcmNNo/WVfJ4xyCLSf0BCOgdTgW6PdaChd1l9VDetJZVEgC5tkyvXsfI
SI6iyrYbKR0NEBSqq4XkadEjsCs4F1RncsS4LlgniT7GlkL9Mce3b0wGLs9/7ZIX
dQIDAQAB
-----END PUBLIC KEY-----"""

app = FastAPI(
    title="JWT Verification API",
    description="Verifies RS256 tokens issued by the assigned identity provider.",
    version="1.0.0",
)


class VerifyRequest(BaseModel):
    token: str


class VerifySuccess(BaseModel):
    valid: Literal[True]
    email: str
    sub: str
    aud: str | list[str]


@app.post(
    "/verify",
    response_model=VerifySuccess,
    responses={
        401: {
            "description": "Invalid token",
            "content": {"application/json": {"example": {"valid": False}}},
        }
    },
)
def verify_token(request: VerifyRequest) -> VerifySuccess | JSONResponse:
    try:
        claims = jwt.decode(
            request.token,
            IDP_PUBLIC_KEY,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={
                "require": ["exp", "iss", "aud", "sub", "email"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
        email = claims["email"]
        subject = claims["sub"]
        audience = claims["aud"]
        if (
            not isinstance(email, str)
            or not isinstance(subject, str)
            or not (
                isinstance(audience, str)
                or (
                    isinstance(audience, list)
                    and all(isinstance(value, str) for value in audience)
                )
            )
        ):
            raise jwt.InvalidTokenError("Invalid required claim type")
    except (jwt.InvalidTokenError, TypeError, ValueError):
        return JSONResponse(status_code=401, content={"valid": False})

    return VerifySuccess(valid=True, email=email, sub=subject, aud=audience)
