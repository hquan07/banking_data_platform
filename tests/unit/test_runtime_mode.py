import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch


RUNTIME_PATH = Path(__file__).resolve().parents[2] / "dashboard/backend/core/runtime.py"


def load_runtime(environment):
    spec = importlib.util.spec_from_file_location("runtime_under_test", RUNTIME_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, environment, clear=True):
        spec.loader.exec_module(module)
    return module


class RuntimeModeTest(unittest.TestCase):
    def test_demo_mode_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "APP_MODE must be integration or production"):
            load_runtime({"APP_MODE": "demo"})

    def test_integration_requires_real_dependency_configuration(self):
        module = load_runtime({"APP_MODE": "integration"})
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, "POSTGRES_USER"):
            module.validate_runtime_config()
