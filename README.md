# LineMQTT

A small Python subscriber for receiving MQTT messages over secure WebSockets (WSS). This first phase is limited to broker connectivity and message logging; it does not include a local broker, FastAPI, database, LINE API, or file transfer.

## Requirements

- Windows host with Python 3.14.10 and the project virtual environment in `.venv`
- Access to `mqtt.kmlinebot.win:443`
- `paho-mqtt` 2.1.0
- A trusted CA bundle at `C:\Program Files\mosquitto\cloudflare-ca.pem` (or another path configured with `MQTT_CA_CERT`)

## Setup

From the repository root, create and activate the virtual environment if it does not already exist, then install dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` locally and set `MQTT_PASSWORD`. Never commit `.env` or paste real credentials into source code. The receiver uses certificate verification and requires the configured CA file; TLS verification is not disabled.

Available settings:

| Variable | Default | Description |
| --- | --- | --- |
| `MQTT_HOST` | `mqtt.kmlinebot.win` | Broker hostname |
| `MQTT_PORT` | `443` | WSS port |
| `MQTT_USERNAME` | `mqttuser` | Broker username |
| `MQTT_PASSWORD` | Required | Broker password |
| `MQTT_TOPIC` | `scg/test` | Subscription topic |
| `MQTT_QOS` | `0` | Subscription QoS |
| `MQTT_CA_CERT` | `C:\Program Files\mosquitto\cloudflare-ca.pem` | CA certificate bundle path |

## Run

With the virtual environment activated, run:

```powershell
python .\mqtt_receiver.py
```

The receiver connects using MQTT v3.1.1 over WSS, subscribes after each successful connection, and writes timestamped connection and message logs to the console. Paho automatically retries the initial connection and reconnects after interruptions with exponential backoff from 1 to 60 seconds. Press Ctrl+C for a graceful shutdown.

## Tests

Run the focused unit tests (all MQTT interactions are mocked; this does not verify live broker connectivity):

```powershell
python -m pytest -q
```
