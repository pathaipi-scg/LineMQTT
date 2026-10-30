"""Secure MQTT-over-WebSockets subscriber for the LineMQTT connectivity test."""

from __future__ import annotations

import logging
import ssl
from typing import Any, Callable

import paho.mqtt.client as mqtt

from config import MQTTConfig, load_config


LOGGER = logging.getLogger("line_mqtt")


def configure_logging() -> None:
    """Configure timestamped console logging."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S%z",
    )


def build_client(
    config: MQTTConfig,
    client_factory: Callable[..., Any] | None = None,
) -> Any:
    """Create and configure a Paho v2 client with verified WSS transport."""

    factory = client_factory or mqtt.Client
    client = factory(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="linemqtt-subscriber",
        protocol=mqtt.MQTTv311,
        transport="websockets",
    )
    client.username_pw_set(config.username, config.password)
    client.ws_set_options(path="/")
    client.tls_set(ca_certs=config.ca_cert, cert_reqs=ssl.CERT_REQUIRED)
    client.tls_insecure_set(False)
    client.reconnect_delay_set(
        min_delay=config.reconnect_min_delay,
        max_delay=config.reconnect_max_delay,
    )

    def on_connect(
        connected_client: Any,
        _userdata: Any,
        _connect_flags: Any,
        reason_code: Any,
        _properties: Any,
    ) -> None:
        if getattr(reason_code, "is_failure", False):
            LOGGER.error("MQTT connection rejected: %s", reason_code)
            return

        LOGGER.info("Connected to MQTT broker %s:%s over WSS", config.host, config.port)
        result, message_id = connected_client.subscribe(config.topic, qos=config.qos)
        if result == mqtt.MQTT_ERR_SUCCESS:
            LOGGER.info(
                "Subscribed to topic %s at QoS %s (message id %s)",
                config.topic,
                config.qos,
                message_id,
            )
        else:
            LOGGER.error("Subscription to %s failed with code %s", config.topic, result)

    def on_disconnect(
        _disconnected_client: Any,
        _userdata: Any,
        _disconnect_flags: Any,
        reason_code: Any,
        _properties: Any,
    ) -> None:
        if getattr(reason_code, "is_failure", False):
            LOGGER.warning("Disconnected from MQTT broker: %s; reconnecting", reason_code)
        else:
            LOGGER.info("Disconnected from MQTT broker")

    def on_message(
        _message_client: Any,
        _userdata: Any,
        message: Any,
    ) -> None:
        payload = message.payload.decode("utf-8", errors="replace")
        # %r escapes newlines and control characters to keep log entries unambiguous.
        LOGGER.info(
            "Received topic=%s qos=%s retained=%s payload=%r",
            message.topic,
            message.qos,
            message.retain,
            payload,
        )

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    return client


def run_receiver(
    config: MQTTConfig,
    client_factory: Callable[..., Any] | None = None,
) -> None:
    """Run the subscriber until interrupted; Paho handles reconnect backoff."""

    client = build_client(config, client_factory=client_factory)
    LOGGER.info("Starting MQTT subscriber for %s", config.topic)
    try:
        client.connect_async(config.host, config.port, keepalive=config.keepalive)
        # Paho loop_forever retries an initial connection when requested and
        # reconnects subsequent interruptions using reconnect_delay_set above.
        client.loop_forever(retry_first_connection=True)
    except KeyboardInterrupt:
        LOGGER.info("Shutdown requested; disconnecting")
    finally:
        client.disconnect()


def main() -> int:
    configure_logging()
    try:
        config = load_config()
    except (OSError, ValueError) as exc:
        LOGGER.error("Invalid MQTT configuration: %s", exc)
        return 2

    try:
        run_receiver(config)
    except KeyboardInterrupt:
        LOGGER.info("Shutdown complete")
    except (OSError, mqtt.MQTTException) as exc:
        LOGGER.error("MQTT receiver stopped: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
