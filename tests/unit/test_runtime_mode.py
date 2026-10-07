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
    def test_mock_requires_demo_mode(self):
        with self.assertRaisesRegex(RuntimeError, "APP_MODE=demo"):
            load_runtime({"APP_MODE": "integration", "ENABLE_MOCK_DATA": "true"})

    def test_demo_allows_explicit_mock(self):
        module = load_runtime({"APP_MODE": "demo", "ENABLE_MOCK_DATA": "true"})
        self.assertTrue(module.demo_mode())

    def test_integration_requires_real_dependency_configuration(self):
        module = load_runtime({"APP_MODE": "integration", "ENABLE_MOCK_DATA": "false"})
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, "POSTGRES_USER"):
            module.validate_runtime_config()
