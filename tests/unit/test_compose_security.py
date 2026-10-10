from pathlib import Path

import yaml


COMPOSE_PATH = Path(__file__).resolve().parents[2] / "docker-compose.yml"


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
