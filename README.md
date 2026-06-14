# Move Smart — Real-Time Smart City Data Pipeline

A streaming data pipeline that simulates a connected vehicle driving from Tinley
Park to Chicago and processes its telemetry end to end: **Kafka → Spark Structured
Streaming → AWS S3 (Parquet) → Redshift Spectrum**.

```
 main.py (producer)         spark-city.py (consumer)
 ┌──────────────┐  Kafka   ┌────────────────────┐  Parquet  ┌──────┐  external  ┌──────────┐
 │ vehicle/gps/ │ ───────▶ │ Spark Structured   │ ────────▶ │  S3  │ ─ schema ▶ │ Redshift │
 │ traffic/...  │  topics  │ Streaming + schema │           │      │            │ Spectrum │
 └──────────────┘          └────────────────────┘           └──────┘            └──────────┘
```

The producer emits five correlated event types per tick — **vehicle, GPS,
traffic-camera, weather, and emergency** — keyed by event id. Spark reads each
topic with an explicit schema, applies a watermark, and writes append-mode
Parquet to S3, where Redshift Spectrum queries it via an external schema.

## Quick start

### 1. Try the generator with no infrastructure

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python jobs/main.py --dry-run --max-ticks 5   # prints events to stdout
```

`--dry-run` needs no Kafka, no AWS, no API key (weather falls back to synthetic
values). Good for inspecting the event payloads.

### 2. Run the full pipeline

```bash
cp .env.example .env        # fill in AWS keys, S3 bucket, optional weather key
docker compose up -d        # Kafka, Zookeeper, Spark master + workers

# produce events to Kafka
python jobs/main.py

# submit the Spark streaming job
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:3.5.0,org.apache.hadoop:hadoop-aws:3.3.1,com.amazonaws:aws-java-sdk:1.11.469 \
  jobs/spark-city.py
```

Then create the external schema and query the data:

```sql
create external schema dev_smartcity
from data catalog database smartcity
iam_role '<your-redshift-s3-role-arn>'
region 'us-east-1';

select * from dev_smartcity.gps_data;
```

## Configuration

All settings come from environment variables (see `.env.example`) — **no secrets
in source**. `jobs/config.py` reads them; `.env` is gitignored.

| Variable | Purpose | Default |
|---|---|---|
| `KAFKA_BOOTSTRAP_SERVERS` | Producer broker (from host) | `localhost:9092` |
| `KAFKA_BOOTSTRAP_SERVERS_INTERNAL` | Broker as seen by Spark container | `broker:29092` |
| `OPENWEATHERMAP_API_KEY` | Live weather (optional) | unset → synthetic |
| `EMIT_INTERVAL_SECONDS` | Seconds between ticks | `3` |
| `AWS_ACCESS_KEY` / `AWS_SECRET_KEY` | S3 write credentials | — |
| `S3_BUCKET` | Bucket for data + checkpoints | `spark-streaming-data` |

## Components

- **`jobs/main.py`** — telemetry generator / Kafka producer (`--dry-run` and `--max-ticks` for testing)
- **`jobs/spark-city.py`** — Spark Structured Streaming consumer → Parquet on S3
- **`jobs/config.py`** — environment-based configuration (no secrets)
- **`docker-compose.yml`** — Kafka, Zookeeper, Spark master + 2 workers
- **`redshift-query.sql`** — Redshift Spectrum external schema

## Stack

Python · Apache Kafka · Apache Spark (Structured Streaming) · AWS S3 · AWS Redshift Spectrum · Docker Compose
