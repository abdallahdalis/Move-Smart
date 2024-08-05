import os
import random
import time
import uuid
import requests

from confluent_kafka import SerializingProducer
import simplejson as json
from datetime import datetime, timedelta

# Coordinates
TINLEY_PARK_COORDINATES = {"latitude": 41.5734, "longitude": -87.7845}
CHICAGO_COORDINATES = {"latitude": 41.8781, "longitude": -87.6298}

# Calculate movement increments
LATITUDE_INCREMENT = (CHICAGO_COORDINATES['latitude'] - TINLEY_PARK_COORDINATES['latitude']) / 100
LONGITUDE_INCREMENT = (CHICAGO_COORDINATES['longitude'] - TINLEY_PARK_COORDINATES['longitude']) / 100

# Output the increments for verification
print("Latitude Increment:", LATITUDE_INCREMENT)
print("Longitude Increment:", LONGITUDE_INCREMENT)

# Environment Variables for configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
VEHICLE_TOPIC = os.getenv('VEHICLE_TOPIC', 'vehicle_data')
GPS_TOPIC = os.getenv('GPS_TOPIC', 'gps_data')
TRAFFIC_TOPIC = os.getenv('TRAFFIC_TOPIC', 'traffic_data')
WEATHER_TOPIC = os.getenv('WEATHER_TOPIC', 'weather_data')
EMERGENCY_TOPIC = os.getenv('EMERGENCY_TOPIC', 'emergency_data')
OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY', '444ba70565e5e10b6d17e538ef2c6dd5')

random.seed(42)
start_time = datetime.now()
start_location = TINLEY_PARK_COORDINATES.copy()

def get_next_time():
    global start_time
    start_time += timedelta(seconds=random.randint(30, 60))  # update frequency
    return start_time

def generate_gps_data(device_id, timestamp, vehicle_type='private'):
    return {
        'id': uuid.uuid4(),
        'deviceId': device_id,
        'timestamp': timestamp,
        'speed': random.uniform(0, 60),  # mph
        'direction': 'North-East',
        'vehicleType': vehicle_type
    }

def generate_traffic_camera_data(device_id, timestamp, location, camera_id):
    return {
        'id': uuid.uuid4(),
        'deviceId': device_id,
        'cameraId': camera_id,
        'location': location,
        'timestamp': timestamp,
        'snapshot': 'Base64EncodedString'
    }

def fetch_weather_data(location):
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={location['latitude']}&lon={location['longitude']}&units=imperial&appid={OPENWEATHERMAP_API_KEY}"
    response = requests.get(url)
    weather_data = response.json()

    # Debug print the API response
    print("Weather API response:", weather_data)

    if 'main' not in weather_data:
        raise ValueError("Missing 'main' in weather data")
    
    if 'weather' not in weather_data:
        raise ValueError("Missing 'weather' in weather data")

    return weather_data

def generate_weather_data(device_id, timestamp, location):
    weather_data = fetch_weather_data(location)
    return {
        'id': uuid.uuid4(),
        'deviceId': device_id,
        'location': location,
        'timestamp': timestamp,
        'temperature': weather_data['main']['temp'],
        'weatherCondition': weather_data['weather'][0]['description'],
        'precipitation': weather_data['rain']['1h'] if 'rain' in weather_data else 0,
        'windSpeed': weather_data['wind']['speed'],
        'humidity': weather_data['main']['humidity'],
        'airQualityIndex': random.uniform(0, 500)  # AQL Value is a placeholder
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
        'description': 'Description of the incident'
    }

def simulate_vehicle_movement():
    global start_location
    # move towards chicago
    start_location['latitude'] += LATITUDE_INCREMENT
    start_location['longitude'] += LONGITUDE_INCREMENT

    # add some randomness to simulate actual road travel
    start_location['latitude'] += random.uniform(-0.0005, 0.0005)
    start_location['longitude'] += random.uniform(-0.0005, 0.0005)

    return start_location

def generate_vehicle_data(device_id):
    location = simulate_vehicle_movement()
    return {
        'id': uuid.uuid4(),
        'deviceId': device_id,
        'timestamp': get_next_time().isoformat(),
        'location': location,  # Corrected usage
        'speed': random.uniform(10, 60),
        'direction': 'North-East',
        'make': 'Nissan',
        'model': 'Altima',
        'year': 2022,
        'fuelType': 'Gas'
    }

def json_serializer(obj):
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

def produce_data_to_kafka(producer, topic, data):
    producer.produce(
        topic,
        key=str(data['id']),
        value=json.dumps(data, default=json_serializer).encode('utf-8'),
        on_delivery=delivery_report
    )

    producer.flush()

def simulate_journey(producer, device_id):
    while True:
        vehicle_data = generate_vehicle_data(device_id)
        gps_data = generate_gps_data(device_id, vehicle_data['timestamp'])
        traffic_camera_data = generate_traffic_camera_data(device_id, vehicle_data['timestamp'],
                                                           vehicle_data['location'], 'GoPro-Cam123')
        weather_data = generate_weather_data(device_id, vehicle_data['timestamp'], vehicle_data['location'])
        emergency_incident_data = generate_emergency_incident_data(device_id, vehicle_data['timestamp'],
                                                                   vehicle_data['location'])

        if (vehicle_data['location']['latitude'] >= CHICAGO_COORDINATES['latitude']
                and vehicle_data['location']['longitude'] <= CHICAGO_COORDINATES['longitude']):
            print('Vehicle has reached Chicago. Simulation ending...')
            break

        produce_data_to_kafka(producer, VEHICLE_TOPIC, vehicle_data)
        produce_data_to_kafka(producer, GPS_TOPIC, gps_data)
        produce_data_to_kafka(producer, TRAFFIC_TOPIC, traffic_camera_data)
        produce_data_to_kafka(producer, WEATHER_TOPIC, weather_data)
        produce_data_to_kafka(producer, EMERGENCY_TOPIC, emergency_incident_data)

        time.sleep(3)

if __name__ == "__main__":
    producer_config = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'error_cb': lambda err: print(f'Kafka error: {err}')
    }
    producer = SerializingProducer(producer_config)

    try:
        simulate_journey(producer, 'Vehicle-ADalis-123')

    except KeyboardInterrupt:
        print('Simulation ended by the user')
    except Exception as e:
        print(f'Unexpected Error occurred: {e}')