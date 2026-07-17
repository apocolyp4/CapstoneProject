import json
import boto3
from datetime import datetime

def check_for_delay(journey):
    expected_arrival = journey.get("expectedArrival") 
    insert_time = journey.get("timing", {}).get("insert")
    
    if not expected_arrival or not insert_time:
        return 0

    # Parse the ISO 8601 timestamps into datetime objects
    expected_arrival = datetime.fromisoformat(expected_arrival.replace("Z", "+00:00"))
    insert_time = datetime.fromisoformat(insert_time.replace("Z", "+00:00"))
    
    # Calculate the time difference in seconds
    time_difference = expected_arrival - insert_time
    total_seconds = time_difference.total_seconds()
    
    # Convert the time difference to minutes
    minutes_to_arrival = round(total_seconds / 60.0)

    return minutes_to_arrival

def get_latest_journey_data(arrivals_data):
    latest_arrivals_data = {}
    
    for journey in arrivals_data:
        trip_id = str(journey.get("tripId", "Unknown"))
        if trip_id == "Unknown":
            continue
            
        # Get the snapshot/record timestamp
        record_timestamp_str = journey.get("timestamp") or journey.get("timing", {}).get("sent")
        if not record_timestamp_str:
            continue
            
        record_timestamp = datetime.fromisoformat(record_timestamp_str.replace("Z", "+00:00"))
        
        # If we haven't seen this trip yet, or if this record is newer than the one we stored, update it
        if trip_id not in  latest_arrivals_data:
             latest_arrivals_data[trip_id] = (record_timestamp, journey)
        else:
            stored_timestamp, _ =  latest_arrivals_data[trip_id]
            if record_timestamp > stored_timestamp:
                 latest_arrivals_data[trip_id] = (record_timestamp, journey)
    
    return latest_arrivals_data


file_name = "aws_credentials.json"

# Load the credentials from a JSON file
try:
    with open(file_name) as file:
        credentials = json.load(file)
except FileNotFoundError:
    print("Error: " + file_name + " file not found.")
    exit(1)


access_key = credentials['access_key']
secret_key = credentials['secret_key']
region = "eu-west-1"
client_type = "s3"
bucket_name = "zxdavebronze"
file_path = "line_244_arrivals.json"
cloudwatch_namespace = "TfLBusMetrics"
metric_name = "Delay_Minutes"


s3_client = boto3.client(client_type, aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
cloudwatch = boto3.client('cloudwatch', aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)

arrivals_file = s3_client.get_object(Bucket=bucket_name, Key=file_path)
arrivals_data = json.loads(arrivals_file['Body'].read())

# Ensure the data is a list to prevent looping issues if it's a single dictionary
if isinstance(arrivals_data, dict):
    arrivals_data = [arrivals_data]

#remove older data and keep only the latest snapshot for each tripId
latest_arrivals_data = get_latest_journey_data(arrivals_data)


for trip_id, (timestamp, journey) in latest_arrivals_data.items():
    delay_minutes = check_for_delay(journey)
    route = journey.get("lineName", "244")
    destination = journey.get("destinationName", "Unknown Destination")
   
    if delay_minutes > 0:
        try:
            cloudwatch.put_metric_data(
                Namespace=cloudwatch_namespace,
                MetricData=[
                    {
                        'MetricName': metric_name,
                        'Dimensions': [
                            {'Name': 'Route', 'Value': route},
                            {'Name': 'TripId', 'Value': trip_id},
                            {'Name': 'Destination', 'Value': destination}
                        ],
                        'Value': float(delay_minutes),
                        'Unit': 'None'
                    }
                ]
            )
            print(f"   Metric successfully sent for TripId: {trip_id} (Snapshot: {timestamp})")
        except Exception as e:
            print(f"   Error: Failed to send metric: {e}")

print("Processing complete.")