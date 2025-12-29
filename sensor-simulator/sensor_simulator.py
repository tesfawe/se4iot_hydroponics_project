import paho.mqtt.client as mqtt
import time
import json
import random
import os
import yaml
from pathlib import Path

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER", "admin")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "admin")
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL", 5))  # seconds
DOMAIN = os.getenv("DOMAIN", "agriculture")


CONFIG_FILE = Path(os.getenv("CONFIG_FILE", "config.yaml"))


GREENHOUSES = []
SENSORS = {}
CONFIG_LAST_MODIFIED = None

def get_unit(sensor_name):
    units = {
        "temperature": "°C",
        "humidity": "%",
        "water_ph": "pH",
        "ec": "mS/cm",
        "water_temperature": "°C",
        "light": "µmol/m²/s"
    }
    return units.get(sensor_name, "")

def generate_value(base, fluctuation):
    return round(random.uniform(base - fluctuation, base + fluctuation), 2)

def load_config():
    global GREENHOUSES, SENSORS, CONFIG_LAST_MODIFIED
    if not CONFIG_FILE.exists():
        print(f"Config file {CONFIG_FILE} not found. Exiting.")
        exit(1)

    mtime = CONFIG_FILE.stat().st_mtime
    if CONFIG_LAST_MODIFIED != mtime:
        with open(CONFIG_FILE) as f:
            config = yaml.safe_load(f)
            GREENHOUSES = config.get("greenhouses", [])
            SENSORS = config.get("sensors", {})
            CONFIG_LAST_MODIFIED = mtime
            print(f"Config reloaded: {len(GREENHOUSES)} greenhouses, {len(SENSORS)} sensors")

def publish_data(client):
    for greenhouse in GREENHOUSES:
        for sensor_name, params in SENSORS.items():
            for sensor_id in params["ids"]:
                value = generate_value(params["base"], params["fluctuation"])
                topic = f"/{DOMAIN}/{greenhouse}/{sensor_name}/{sensor_id}"

                payload = {
                    "sensor_name": sensor_name,
                    "sensor_id": sensor_id,
                    "location": greenhouse,
                    "value": value,
                    "unit": get_unit(sensor_name),
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
        except:
            time.sleep(5)


def main():
    client = mqtt.Client(client_id="Python_Hydroponics_Simulator")
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_disconnect = on_disconnect

    # Initial MQTT connection
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            print("Connected to MQTT broker!")
            break
        except Exception as e:
            print(f"Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

    client.loop_start()

    # Continuous loop
    while True:
        load_config()  # hot-reload config if modified
        publish_data(client)
        interval = random.uniform(PUBLISH_INTERVAL * 0.8, PUBLISH_INTERVAL * 1.2)
        time.sleep(interval)

if __name__ == "__main__":
    main()
