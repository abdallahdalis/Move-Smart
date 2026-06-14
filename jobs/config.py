"""Configuration loaded from environment variables.

This file contains NO secrets and is safe to commit. Copy `.env.example` to
`.env` and fill in your values, or export the variables in your shell.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

configuration = {
    "AWS_ACCESS_KEY": os.getenv("AWS_ACCESS_KEY", ""),
    "AWS_SECRET_KEY": os.getenv("AWS_SECRET_KEY", ""),
    "AWS_REGION": os.getenv("AWS_REGION", "us-east-1"),
    # S3 bucket (without the s3a:// prefix) for streamed data + checkpoints
    "S3_BUCKET": os.getenv("S3_BUCKET", "spark-streaming-data"),
    # Kafka bootstrap servers as seen from inside the Spark container
    "KAFKA_BOOTSTRAP_SERVERS": os.getenv("KAFKA_BOOTSTRAP_SERVERS_INTERNAL", "broker:29092"),
}
