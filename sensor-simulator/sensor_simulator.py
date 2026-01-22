import paho.mqtt.client as mqtt
import time
import json
import random
import os
import yaml
from pathlib import Path

# MQTT connection params from environment
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER", "admin")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "admin")
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL", 5))  # seconds
DOMAIN = os.getenv("DOMAIN", "agriculture")

# Config file path (mounted by docker-compose)
CONFIG_FILE = Path(os.getenv("CONFIG_FILE", "/app/config/config.yaml"))

GREENHOUSES = []
SIM_SENSORS = {}
RUNTIME_SENSORS = {}
CONFIG_LAST_MODIFIED = None


def generate_value(base, fluctuation):
    return round(random.uniform(base - fluctuation, base + fluctuation), 2)


def load_config():
    global GREENHOUSES, SIM_SENSORS, RUNTIME_SENSORS, CONFIG_LAST_MODIFIED

    if not CONFIG_FILE.exists():
        print(f"Config file {CONFIG_FILE} not found. Exiting.")
        exit(1)

    mtime = CONFIG_FILE.stat().st_mtime
    if CONFIG_LAST_MODIFIED != mtime:
        with open(CONFIG_FILE) as f:
            config = yaml.safe_load(f) or {}

        # Runtime sensors (unit + thresholds)
        RUNTIME_SENSORS = config.get("sensors", {})

        # Simulator-specific section
        sim_cfg = config.get("simulator", {})
        GREENHOUSES = sim_cfg.get("greenhouses", [])
        SIM_SENSORS = sim_cfg.get("sensors", {})

        CONFIG_LAST_MODIFIED = mtime
        print(
            f"Config reloaded: {len(GREENHOUSES)} greenhouses, "
            f"{len(SIM_SENSORS)} simulator sensors, "
            f"{len(RUNTIME_SENSORS)} runtime sensor types"
        )


def publish_data(client):
    for greenhouse in GREENHOUSES:
        for sensor_name, params in SIM_SENSORS.items():
            base = params["base"]
            fluct = params["fluctuation"]

            # Try to get unit from runtime sensors definition
            unit = ""
            runtime_cfg = RUNTIME_SENSORS.get(sensor_name)
            if runtime_cfg:
                unit = runtime_cfg.get("unit", "")

            for sensor_id in params["ids"]:
                value = generate_value(base, fluct)
                topic = f"/{DOMAIN}/{greenhouse}/{sensor_name}/{sensor_id}"

                payload = {
                    "sensor_name": sensor_name,
                    "sensor_id": sensor_id,
                    "location": greenhouse,
                    "value": value,
                    "unit": unit,
                    "timestamp": int(time.time() * 1000)
                }

                client.publish(topic, json.dumps(payload), qos=1)
                print(f"Published to {topic}: {payload}")


def on_disconnect(client, userdata, rc):
    print("Disconnected from MQTT! Attempting to reconnect...")
    while True:
        try:
            client.reconnect()
            print("Reconnected successfully.")
            break
        except Exception:
            time.sleep(5)


def main():
    client = mqtt.Client(client_id="Python_Hydroponics_Simulator")
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_disconnect = on_disconnect

    # Initial connection loop
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            print("Connected to MQTT broker!")
            break
        except Exception as e:
            print(f"Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

    client.loop_start()

    # Main loop
    while True:
        load_config()  # hot-reload config if modified
        publish_data(client)
        interval = random.uniform(PUBLISH_INTERVAL * 0.8, PUBLISH_INTERVAL * 1.2)
        time.sleep(interval)


if __name__ == "__main__":
    main()
