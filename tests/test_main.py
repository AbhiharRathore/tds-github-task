import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main


class EffectiveConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main.app)
        self.environment = patch.dict(
            os.environ,
            {
                "APP_ENV": "development",
                "APP_WORKERS": "1",
                "APP_DEBUG": "true",
                "APP_LOG_LEVEL": "warning",
            },
            clear=True,
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_base_response_uses_env_and_os_layers(self) -> None:
        response = self.client.get("/effective-config")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "port": 8763,
                "workers": 1,
                "debug": True,
                "log_level": "warning",
                "api_key": "****",
            },
        )

    def test_unencoded_equals_in_query_value(self) -> None:
        response = self.client.get("/effective-config?set=port=9000")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["port"], 9000)
        self.assertIs(type(response.json()["port"]), int)

    def test_repeated_query_overrides_use_first_equals_and_win(self) -> None:
        response = self.client.get(
            "/effective-config?set=port%3D9000&set=debug%3Dfalse"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "port": 9000,
                "workers": 1,
                "debug": False,
                "log_level": "warning",
                "api_key": "****",
            },
        )
        self.assertIs(type(response.json()["workers"]), int)

    def test_string_override_preserves_additional_equals(self) -> None:
        response = self.client.get(
            "/effective-config?set=log_level%3Derror%3Ddetail"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["log_level"], "error=detail")

    def test_debug_boolean_values_are_case_insensitive(self) -> None:
        for value in ("true", "1", "yes", "on", "TRUE"):
            with self.subTest(value=value):
                response = self.client.get(
                    "/effective-config", params={"set": f"debug={value}"}
                )
                self.assertTrue(response.json()["debug"])

        for value in ("false", "0", "no", "off", "other"):
            with self.subTest(value=value):
                response = self.client.get(
                    "/effective-config", params={"set": f"debug={value}"}
                )
                self.assertFalse(response.json()["debug"])

    def test_invalid_integer_returns_clear_bad_request(self) -> None:
        for key in ("port", "workers"):
            with self.subTest(key=key):
                response = self.client.get(
                    "/effective-config", params={"set": f"{key}=not-an-int"}
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json()["detail"],
                    f"Invalid integer for configuration key '{key}'",
                )

    def test_unknown_and_malformed_overrides_return_bad_request(self) -> None:
        unknown = self.client.get("/effective-config?set=extra%3Dvalue")
        malformed = self.client.get("/effective-config?set=not-a-pair")

        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(malformed.status_code, 400)

    def test_worker_alias_and_query_api_key_masking(self) -> None:
        with patch.dict(os.environ, {"NUM_WORKERS": "7"}):
            self.assertEqual(self.client.get("/effective-config").json()["workers"], 7)

        with patch.object(
            main,
            "load_dotenv_config",
            return_value={"NUM_WORKERS": "9"},
        ):
            with patch.dict(os.environ):
                os.environ.pop("APP_WORKERS", None)
                self.assertEqual(
                    self.client.get("/effective-config").json()["workers"], 9
                )

        response = self.client.get("/effective-config?set=api_key%3Dquery-secret")
        self.assertEqual(response.json()["api_key"], "****")


if __name__ == "__main__":
    unittest.main()
