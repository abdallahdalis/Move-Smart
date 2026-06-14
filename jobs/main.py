"""Smart-city telemetry generator.

Simulates a vehicle driving from Tinley Park to Chicago, emitting vehicle, GPS,
traffic-camera, weather, and emergency events to Kafka.

Run modes:
    python jobs/main.py            # stream to Kafka (needs a running broker)
    python jobs/main.py --dry-run  # print events to stdout, no Kafka required
"""
import argparse
import os
import random
import time
import uuid
from datetime import datetime, timedelta

import requests
import simplejson as json
from confluent_kafka import SerializingProducer

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional; env vars still work without it

# Coordinates
TINLEY_PARK_COORDINATES = {"latitude": 41.5734, "longitude": -87.7845}
CHICAGO_COORDINATES = {"latitude": 41.8781, "longitude": -87.6298}

# Movement increments (100 steps from Tinley Park to Chicago)
LATITUDE_INCREMENT = (CHICAGO_COORDINATES['latitude'] - TINLEY_PARK_COORDINATES['latitude']) / 100
LONGITUDE_INCREMENT = (CHICAGO_COORDINATES['longitude'] - TINLEY_PARK_COORDINATES['longitude']) / 100

# Configuration (all via environment; no secrets in source)
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
VEHICLE_TOPIC = os.getenv('VEHICLE_TOPIC', 'vehicle_data')
GPS_TOPIC = os.getenv('GPS_TOPIC', 'gps_data')
TRAFFIC_TOPIC = os.getenv('TRAFFIC_TOPIC', 'traffic_data')
WEATHER_TOPIC = os.getenv('WEATHER_TOPIC', 'weather_data')
EMERGENCY_TOPIC = os.getenv('EMERGENCY_TOPIC', 'emergency_data')
OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')  # required only for live weather
EMIT_INTERVAL_SECONDS = float(os.getenv('EMIT_INTERVAL_SECONDS', '3'))

random.seed(42)
start_time = datetime.now()
start_location = TINLEY_PARK_COORDINATES.copy()


def get_next_time():
    global start_time
    start_time += timedelta(seconds=random.randint(30, 60))
    return start_time


def generate_gps_data(device_id, timestamp, vehicle_type='private'):
    return {
        'id': uuid.uuid4(),
        'deviceId': device_id,
        'timestamp': timestamp,
        'speed': random.uniform(0, 60),  # mph
        'direction': 'North-East',
        'vehicleType': vehicle_type,
    }


def generate_traffic_camera_data(device_id, timestamp, location, camera_id):
    return {
        'id': uuid.uuid4(),
        'deviceId': device_id,
        'cameraId': camera_id,
        'location': location,
        'timestamp': timestamp,
        'snapshot': 'Base64EncodedString',
    }


def fetch_weather_data(location):
    """Fetch live weather; raise on any failure so the caller can fall back."""
    if not OPENWEATHERMAP_API_KEY:
        raise RuntimeError("OPENWEATHERMAP_API_KEY not set")
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={location['latitude']}&lon={location['longitude']}"
        f"&units=imperial&appid={OPENWEATHERMAP_API_KEY}"
    )
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    weather_data = response.json()
    if 'main' not in weather_data or 'weather' not in weather_data:
        raise ValueError(f"Unexpected weather payload: {weather_data}")
    return weather_data


def generate_weather_data(device_id, timestamp, location):
    """Return a weather event, using live data when available and synthetic
    values as a fallback so a transient API failure never stops the stream."""
    try:
        w = fetch_weather_data(location)
        temperature = w['main']['temp']
        condition = w['weather'][0]['description']
        precipitation = w.get('rain', {}).get('1h', 0)
        wind_speed = w['wind']['speed']
        humidity = w['main']['humidity']
    except Exception as e:
        print(f"[weather] live fetch failed ({e}); using synthetic values")
        temperature = round(random.uniform(20, 90), 1)
        condition = random.choice(['clear sky', 'few clouds', 'light rain', 'snow'])
        precipitation = round(random.uniform(0, 5), 2)
        wind_speed = round(random.uniform(0, 25), 1)
        humidity = random.randint(20, 100)
    return {
        'id': uuid.uuid4(),
        'deviceId': device_id,
        'location': location,
        'timestamp': timestamp,
        'temperature': temperature,
        'weatherCondition': condition,
        'precipitation': precipitation,
        'windSpeed': wind_speed,
        'humidity': humidity,
        'airQualityIndex': round(random.uniform(0, 500), 1),  # placeholder AQI
    }


def generate_emergency_incident_data(device_id, timestamp, location):
    return {
        'id': uuid.uuid4(),
        'deviceId': device_id,
        'incidentId': uuid.uuid4(),
        'type': random.choice(['Accident', 'Fire', 'Medical', 'Police', 'None']),
        'timestamp': timestamp,
        'location': location,
        'status': random.choice(['Active', 'Resolved']),
        'description': 'Description of the incident',
    }


def simulate_vehicle_movement():
    global start_location
    start_location['latitude'] += LATITUDE_INCREMENT
    start_location['longitude'] += LONGITUDE_INCREMENT
    # jitter to mimic real road travel
    start_location['latitude'] += random.uniform(-0.0005, 0.0005)
    start_location['longitude'] += random.uniform(-0.0005, 0.0005)
    return start_location


def generate_vehicle_data(device_id):
    location = simulate_vehicle_movement()
    return {
        'id': uuid.uuid4(),
        'deviceId': device_id,
        'timestamp': get_next_time().isoformat(),
        'location': location,
        'speed': random.uniform(10, 60),
        'direction': 'North-East',
        'make': 'Nissan',
        'model': 'Altima',
        'year': 2022,
        'fuelType': 'Gas',
    }


def json_serializer(obj):
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')


def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')


def produce_data_to_kafka(producer, topic, data):
    producer.produce(
        topic,
        key=str(data['id']),
        value=json.dumps(data, default=json_serializer).encode('utf-8'),
        on_delivery=delivery_report,
    )
    producer.poll(0)  # serve delivery callbacks without a full flush each message


def build_events(device_id):
    """Generate one tick of correlated events for a device."""
    vehicle = generate_vehicle_data(device_id)
    ts, loc = vehicle['timestamp'], vehicle['location']
    return {
        VEHICLE_TOPIC: vehicle,
        GPS_TOPIC: generate_gps_data(device_id, ts),
        TRAFFIC_TOPIC: generate_traffic_camera_data(device_id, ts, loc, 'GoPro-Cam123'),
        WEATHER_TOPIC: generate_weather_data(device_id, ts, loc),
        EMERGENCY_TOPIC: generate_emergency_incident_data(device_id, ts, loc),
    }


def reached_chicago(location):
    return (location['latitude'] >= CHICAGO_COORDINATES['latitude']
            and location['longitude'] <= CHICAGO_COORDINATES['longitude'])


def simulate_journey(producer, device_id, dry_run=False, max_ticks=None):
    ticks = 0
    while True:
        events = build_events(device_id)
        if reached_chicago(events[VEHICLE_TOPIC]['location']):
            print('Vehicle has reached Chicago. Simulation ending...')
            break

        if dry_run:
            for topic, data in events.items():
                print(f'{topic}: {json.dumps(data, default=json_serializer)}')
        else:
            for topic, data in events.items():
                produce_data_to_kafka(producer, topic, data)
            producer.flush()  # one flush per tick (5 messages), not per message

        ticks += 1
        if max_ticks and ticks >= max_ticks:
            print(f'Reached max_ticks={max_ticks}; stopping.')
            break
        time.sleep(EMIT_INTERVAL_SECONDS)


def parse_args():
    p = argparse.ArgumentParser(description='Smart-city telemetry generator')
    p.add_argument('--dry-run', action='store_true',
                   help='print events to stdout instead of producing to Kafka')
    p.add_argument('--max-ticks', type=int, default=None,
                   help='stop after N ticks (useful for testing)')
    p.add_argument('--device-id', default='Vehicle-ADalis-123')
    return p.parse_args()


def main():
    args = parse_args()

    producer = None
    if not args.dry_run:
        producer = SerializingProducer({
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
            'error_cb': lambda err: print(f'Kafka error: {err}'),
        })

    try:
        simulate_journey(producer, args.device_id,
                         dry_run=args.dry_run, max_ticks=args.max_ticks)
    except KeyboardInterrupt:
        print('Simulation ended by the user')
    finally:
        if producer is not None:
            producer.flush()


if __name__ == "__main__":
    main()
