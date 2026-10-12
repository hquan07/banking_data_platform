from pathlib import Path

import yaml


COMPOSE_PATH = Path(__file__).resolve().parents[2] / "docker-compose.yml"
SECURE_COMPOSE_PATH = Path(__file__).resolve().parents[2] / "docker-compose.secure.yml"


def test_all_published_ports_are_loopback_only():
    compose = yaml.safe_load(COMPOSE_PATH.read_text())
    exposed = [
        (service_name, port)
        for service_name, service in compose["services"].items()
        for port in service.get("ports", [])
    ]

    assert exposed, "Compose should publish the local operator interfaces"
    assert all(
        str(port).startswith("127.0.0.1:")
        for _, port in exposed
    ), exposed


def test_secure_overlay_separates_postgres_identities_and_uses_secret_files():
    compose = yaml.safe_load(SECURE_COMPOSE_PATH.read_text())
    services = compose["services"]
    assert services["dashboard_backend"]["environment"]["POSTGRES_USER"] == "${POSTGRES_API_USER:-banking_api}"
    assert services["dashboard_backend"]["environment"]["POSTGRES_PASSWORD"] == ""
    assert services["dashboard_backend"]["environment"]["RUN_DB_MIGRATIONS"] == "false"
    assert services["postgres_migrate"]["environment"]["POSTGRES_USER"] == "${POSTGRES_MIGRATION_USER:-banking_migration}"
    assert services["payment_processor"]["environment"]["POSTGRES_USER"] == "${POSTGRES_PROCESSOR_USER:-banking_processor}"
    assert services["postgres"]["environment"]["POSTGRES_PASSWORD"] == ""
    assert services["postgres"]["environment"]["POSTGRES_PASSWORD_FILE"] == "/run/secrets/postgres_admin_password"
    assert "postgres_admin_password" in services["postgres"]["secrets"]
    assert "postgres_backup_password" in services["postgres"]["secrets"]
    assert "postgres_monitor_password" in compose["secrets"]
