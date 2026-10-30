from __future__ import annotations

import logging
import ssl
from types import SimpleNamespace
from unittest.mock import MagicMock

import paho.mqtt.client as mqtt
import pytest

from config import MQTTConfig, load_config
from mqtt_receiver import build_client, run_receiver


@pytest.fixture

def mqtt_config() -> MQTTConfig:
    return MQTTConfig(
        host="mqtt.kmlinebot.win",
        port=443,
        username="mqttuser",
        password="unit-test-password",
        topic="scg/test",
        qos=0,
        ca_cert=r"C:\test\ca.pem",
    )


def test_load_config_reads_dotenv_and_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("MQTT_PASSWORD", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "MQTT_PASSWORD=test-secret\nMQTT_CA_CERT=C:/certs/test-ca.pem\n",
        encoding="utf-8",
    )

    config = load_config(env_file)

    assert config.host == "mqtt.kmlinebot.win"
    assert config.port == 443
    assert config.username == "mqttuser"
    assert config.password == "test-secret"
    assert config.topic == "scg/test"
    assert config.qos == 0
    assert config.ca_cert == "C:/certs/test-ca.pem"


def test_load_config_requires_password(tmp_path, monkeypatch):
    monkeypatch.delenv("MQTT_PASSWORD", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("MQTT_HOST=localhost\n", encoding="utf-8")

    with pytest.raises(ValueError, match="MQTT_PASSWORD"):
        load_config(env_file)


def test_build_client_sets_secure_wss_and_subscribes(mqtt_config):
    fake_client = MagicMock()
    fake_client.subscribe.return_value = (mqtt.MQTT_ERR_SUCCESS, 17)
    factory = MagicMock(return_value=fake_client)

    client = build_client(mqtt_config, client_factory=factory)

    factory.assert_called_once_with(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="linemqtt-subscriber",
        protocol=mqtt.MQTTv311,
        transport="websockets",
    )
    fake_client.username_pw_set.assert_called_once_with("mqttuser", "unit-test-password")
    fake_client.ws_set_options.assert_called_once_with(path="/")
    fake_client.tls_set.assert_called_once_with(
        ca_certs=mqtt_config.ca_cert,
        cert_reqs=ssl.CERT_REQUIRED,
    )
    fake_client.tls_insecure_set.assert_called_once_with(False)
    fake_client.reconnect_delay_set.assert_called_once_with(min_delay=1, max_delay=60)

    client.on_connect(client, None, None, SimpleNamespace(is_failure=False), None)
    fake_client.subscribe.assert_called_once_with("scg/test", qos=0)


def test_message_callback_logs_payload_and_topic(mqtt_config, caplog):
    client = build_client(mqtt_config, client_factory=MagicMock())
    caplog.set_level(logging.INFO, logger="line_mqtt")
    message = SimpleNamespace(
        topic="scg/test",
        qos=0,
        retain=False,
        payload="hello\nworld".encode("utf-8"),
    )

    client.on_message(client, None, message)

    assert "topic=scg/test" in caplog.text
    assert r"payload='hello\nworld'" in caplog.text


def test_run_receiver_disconnects_on_ctrl_c(mqtt_config):
    fake_client = MagicMock()
    fake_client.loop_forever.side_effect = KeyboardInterrupt

    run_receiver(mqtt_config, client_factory=MagicMock(return_value=fake_client))

    fake_client.connect_async.assert_called_once_with(
        "mqtt.kmlinebot.win", 443, keepalive=60
    )
    fake_client.loop_forever.assert_called_once_with(retry_first_connection=True)
    fake_client.disconnect.assert_called_once_with()
