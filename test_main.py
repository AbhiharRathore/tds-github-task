import re
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware

import main


client = TestClient(main.app)


def assert_response_metadata(response):
    request_id = response.headers["x-request-id"]
    UUID(request_id)
    assert re.fullmatch(r"\d+\.\d{9}", response.headers["x-process-time"])
    assert float(response.headers["x-process-time"]) >= 0


def test_stats_calculates_values_from_request():
    response = client.get("/stats?values=1,2,3")

    assert response.status_code == 200
    assert response.json() == {
        "email": "23f2003903@ds.study.iitm.ac.in",
        "count": 3,
        "sum": 6,
        "min": 1,
        "max": 3,
        "mean": 2.0,
    }
    assert_response_metadata(response)


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ("-12,4,100", (-12, 100, 92, 92 / 3)),
        ("8", (8, 8, 8, 8.0)),
        (" 2, -4, 9 ", (-4, 9, 7, 7 / 3)),
    ],
)
def test_stats_are_dynamic(values, expected):
    response = client.get("/stats", params={"values": values})

    assert response.status_code == 200
    body = response.json()
    assert (body["min"], body["max"], body["sum"], body["mean"]) == expected
    assert body["count"] == len(values.split(","))
    assert_response_metadata(response)


@pytest.mark.parametrize("values", ["", "1,two,3", "1,,3", "1,"])
def test_invalid_values_return_error_with_metadata(values):
    response = client.get("/stats", params={"values": values})

    assert response.status_code == 422
    assert_response_metadata(response)


def test_missing_values_return_error_with_metadata():
    response = client.get("/stats")

    assert response.status_code == 422
    assert_response_metadata(response)


def test_request_id_is_unique_per_request():
    first = client.get("/stats?values=1")
    second = client.get("/stats?values=1")

    assert first.headers["x-request-id"] != second.headers["x-request-id"]


def test_allowed_origin_preflight_succeeds_with_response_metadata():
    response = client.options(
        "/stats",
        headers={
            "Origin": main.ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == main.ALLOWED_ORIGIN
    assert_response_metadata(response)


def test_allowed_origin_receives_cors_header_on_stats_response():
    response = client.get(
        "/stats?values=1",
        headers={"Origin": main.ALLOWED_ORIGIN},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == main.ALLOWED_ORIGIN
    assert_response_metadata(response)


def test_other_origin_does_not_receive_allow_origin_header():
    response = client.options(
        "/stats",
        headers={
            "Origin": "https://other.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
    assert_response_metadata(response)


def test_not_found_response_has_response_metadata():
    response = client.get("/not-a-route")

    assert response.status_code == 404
    assert_response_metadata(response)


def test_internal_error_response_has_response_metadata(monkeypatch):
    def fail_stats(values):
        raise RuntimeError(f"unexpected failure for {values}")

    monkeypatch.setattr(main, "calculate_stats", fail_stats)
    error_client = TestClient(main.app, raise_server_exceptions=False)

    response = error_client.get("/stats?values=1")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    assert_response_metadata(response)


def test_cors_allows_only_the_assigned_origin():
    cors = next(
        middleware
        for middleware in main.app.user_middleware
        if middleware.cls is CORSMiddleware
    )
    assert cors.kwargs["allow_origins"] == [main.ALLOWED_ORIGIN]
    assert "*" not in cors.kwargs["allow_origins"]


def test_openapi_documents_stats_endpoint():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/stats" in response.json()["paths"]
