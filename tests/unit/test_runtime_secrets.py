import importlib.util
import os
import stat
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SECRETS = _load("runtime_secrets_test", ROOT / "shared/runtime_secrets.py")
BOOTSTRAP = _load(
    "bootstrap_local_secrets_test",
    ROOT / "scripts/security/bootstrap_local_secrets.py",
)


def test_secret_file_takes_precedence_over_environment(tmp_path, monkeypatch):
    path = tmp_path / "password"
    path.write_text("file-value\n")
    monkeypatch.setenv("DATABASE_PASSWORD", "environment-value")
    monkeypatch.setenv("DATABASE_PASSWORD_FILE", str(path))
    assert SECRETS.get_secret("DATABASE_PASSWORD") == "file-value"


def test_missing_required_secret_fails_closed(monkeypatch):
    monkeypatch.delenv("MISSING_SECRET", raising=False)
    monkeypatch.delenv("MISSING_SECRET_FILE", raising=False)
    with pytest.raises(RuntimeError, match="Missing required secret"):
        SECRETS.get_secret("MISSING_SECRET", required=True)


def test_bootstrap_preserves_dedicated_secrets_until_rotation(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_PASSWORD=admin-only-value\n"
        "CLICKHOUSE_PASSWORD=clickhouse-admin-only-value\n"
    )
    directory = tmp_path / "secrets"
    first = BOOTSTRAP.bootstrap(directory, env_file)
    original = (directory / "postgres_api_password").read_text()
    second = BOOTSTRAP.bootstrap(directory, env_file)
    assert "postgres_api_password" in first
    assert "postgres_api_password" not in second
    assert (directory / "postgres_api_password").read_text() == original
    BOOTSTRAP.bootstrap(directory, env_file, rotate=True)
    assert (directory / "postgres_api_password").read_text() != original
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert all(
        stat.S_IMODE(path.stat().st_mode) == 0o444
        for path in directory.iterdir()
    )
