# Move Smart: Real-Time Smart City Data Processing

## Overview

The Move Smart project is a real-time data processing system for a smart city simulation. It integrates various data sources, processes the data using Apache Spark, and stores the results in AWS S3. The system also includes a Redshift external schema for querying the processed data. 

## Components

- **Apache Kafka**: Manages real-time data streaming.
- **Apache Spark**: Processes data streams and writes results to AWS S3.
- **AWS S3**: Stores the processed data.
- **AWS Redshift**: Provides an external schema to query the data stored in S3.

## Directory Structure

- `jobs/`: Contains the Spark job scripts.
  - `config.py`: Configuration settings for the Spark job.
  - `spark-city.py`: Main script for reading from Kafka, processing data with Spark, and writing to S3.
  - `redshift-query.sql`: SQL script for creating an external schema in Redshift.
- `docker-compose.yml`: Docker Compose configuration for setting up Kafka, Zookeeper, Spark, and related services.
- `requirements.txt`: Lists Python dependencies required for the project.

## Setup and Configuration

### Prerequisites

- Docker and Docker Compose
- AWS account with S3 and Redshift setup
- Python 3.x

### Docker Compose Configuration

1. **Kafka and Zookeeper**: Set up Kafka brokers and Zookeeper for managing the Kafka cluster.
2. **Spark**: Configure Spark master and worker nodes.
3. **Networking**: All services are connected via the `datamasterylab` network.

### Dependencies

Install the Python dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

### Configuration

Update `config.py` with your AWS credentials and any other configuration settings required for the project.

### Running the Project

1. **Start Docker Services**: Use Docker Compose to start all services.

   ```bash
   docker-compose up -d
   ```

2. **Run Spark Job**: Submit the Spark job to process data from Kafka and write to S3.

   ```bash
   spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.13:3.5.0,org.apache.hadoop:hadoop-aws:3.3.1,com.amazonaws:aws-java-sdk:1.11.469 jobs/spark-city.py
   ```

3. **Query Data**: Use the provided `redshift-query.sql` script to create an external schema in Redshift and query the data.

   ```sql
   -- Run this script in your Redshift query editor
   create external schema dev_smartcity
   from data catalog
   database smartcity
   iam_role 'arn:aws:iam::6112121121212:role/smart-city-redshift-s3-role'
   region 'us-east-1';

   select * from dev_smartcity.gps_data;
   ```

## Schema Definitions

The following schemas are defined for processing data:

- **Vehicle Schema**: Includes fields like `id`, `deviceId`, `timestamp`, `location`, `speed`, etc.
- **GPS Schema**: Includes fields like `id`, `deviceId`, `timestamp`, `speed`, `direction`, `vehicleType`, etc.
- **Traffic Schema**: Includes fields like `id`, `deviceId`, `cameraId`, `location`, `timestamp`, `snapshot`, etc.
- **Weather Schema**: Includes fields like `id`, `deviceId`, `location`, `timestamp`, `temperature`, `weatherCondition`, etc.
- **Emergency Schema**: Includes fields like `id`, `deviceId`, `incidentId`, `type`, `timestamp`, `location`, `status`, `description`, etc.

## Troubleshooting

- **Spark Job Errors**: Check Spark logs for detailed error messages.
- **Kafka Connectivity**: Ensure that Kafka and Zookeeper are running and properly configured.
- **S3 Access**: Verify that AWS credentials are correct and that the S3 bucket is accessible.
- **Redshift Queries**: Ensure that the IAM role has the necessary permissions and that the external schema is created successfully.

---

Feel free to modify the content according to your specific needs or preferences.
