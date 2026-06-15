"""Hot-reload marker for AI_GATEWAY_MODULES_CONFIG."""

from __future__ import annotations

import json
import os
import tempfile
import time
import unittest

import gateway_config


class TestGatewayConfigReload(unittest.TestCase):
    def test_maybe_reload_on_mtime(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(
                {
                    "modules": {
                        "face": {"enabled": False, "provider": "x", "model": "m", "params": {}},
                    }
                },
                f,
            )
            path = f.name
        try:
            os.environ["AI_GATEWAY_MODULES_CONFIG"] = path
            gateway_config.set_gateway_config(gateway_config.load_gateway_config())
            self.assertFalse(gateway_config.get_gateway_config().module("face").enabled)

            time.sleep(0.15)
            with open(path, "w", encoding="utf-8") as f2:
                json.dump(
                    {
                        "modules": {
                            "face": {"enabled": True, "provider": "x", "model": "m", "params": {}},
                        }
                    },
                    f2,
                )

            self.assertTrue(gateway_config.maybe_reload_gateway_config())
            self.assertTrue(gateway_config.get_gateway_config().module("face").enabled)
            self.assertFalse(gateway_config.maybe_reload_gateway_config())
        finally:
            os.unlink(path)
            del os.environ["AI_GATEWAY_MODULES_CONFIG"]
            gateway_config.set_gateway_config(gateway_config.load_gateway_config())


if __name__ == "__main__":
    unittest.main()
