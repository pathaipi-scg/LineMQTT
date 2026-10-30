"""Configuration loading for the LineMQTT receiver."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_HOST = "mqtt.kmlinebot.win"
DEFAULT_PORT = 443
DEFAULT_USERNAME = "mqttuser"
DEFAULT_TOPIC = "scg/test"
DEFAULT_CA_CERT = r"C:\Program Files\mosquitto\cloudflare-ca.pem"


@dataclass(frozen=True, slots=True)
class MQTTConfig:
    """Validated settings needed to connect to the MQTT service."""

    host: str
    port: int
    username: str
    password: str
    topic: str
    qos: int
    ca_cert: str
    keepalive: int = 60
    reconnect_min_delay: int = 1
    reconnect_max_delay: int = 60


def _read_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default))
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def load_config(env_file: Path | None = None) -> MQTTConfig:
    """Load settings from the project .env file and validate them."""

    load_dotenv(dotenv_path=env_file or Path(__file__).with_name(".env"), override=False)

    password = os.getenv("MQTT_PASSWORD", "")
    if not password:
        raise ValueError("MQTT_PASSWORD must be set in the environment or .env file")

    port = _read_int("MQTT_PORT", DEFAULT_PORT)
    qos = _read_int("MQTT_QOS", 0)
    if not 1 <= port <= 65535:
        raise ValueError("MQTT_PORT must be between 1 and 65535")
    if qos not in (0, 1, 2):
        raise ValueError("MQTT_QOS must be 0, 1, or 2")

    return MQTTConfig(
        host=os.getenv("MQTT_HOST", DEFAULT_HOST),
        port=port,
        username=os.getenv("MQTT_USERNAME", DEFAULT_USERNAME),
        password=password,
        topic=os.getenv("MQTT_TOPIC", DEFAULT_TOPIC),
        qos=qos,
        ca_cert=os.getenv("MQTT_CA_CERT", DEFAULT_CA_CERT),
    )
