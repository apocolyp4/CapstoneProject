      Code:
        ZipFile: |
          import json
          import os
          import boto3
          from datetime import datetime

          def check_for_delay(journey):
              expected_arrival = journey.get("expectedArrival") 
              insert_time = journey.get("timing", {}).get("insert")
              
              if not expected_arrival or not insert_time:
                  return 0

              expected_arrival = datetime.fromisoformat(expected_arrival.replace("Z", "+00:00"))
              insert_time = datetime.fromisoformat(insert_time.replace("Z", "+00:00"))
              
              time_difference = expected_arrival - insert_time
              minutes_to_arrival = round(time_difference.total_seconds() / 60.0)

              return minutes_to_arrival

          def get_latest_journey_data(arrivals_data):
              latest_arrivals_data = {}
              
              for journey in arrivals_data:
                  trip_id = str(journey.get("tripId", "Unknown"))
                  if trip_id == "Unknown":
                      continue
                      
                  record_timestamp_str = journey.get("timestamp") or journey.get("timing", {}).get("sent")
                  if not record_timestamp_str:
                      continue
                      
                  record_timestamp = datetime.fromisoformat(record_timestamp_str.replace("Z", "+00:00"))
                  
                  if trip_id not in latest_arrivals_data:
                       latest_arrivals_data[trip_id] = (record_timestamp, journey)
                  else:
                       stored_timestamp, _ = latest_arrivals_data[trip_id]
                       if record_timestamp > stored_timestamp:
                            latest_arrivals_data[trip_id] = (record_timestamp, journey)
              
              return latest_arrivals_data

          def lambda_handler(event, context):
              bucket_name = os.environ["BUCKET_NAME"]
              file_path = os.environ["FILE_PATH"]
              cloudwatch_namespace = os.environ["CLOUDWATCH_NAMESPACE"]
              metric_name = os.environ["METRIC_NAME"]

              status_200_metric = os.environ["STATUS_200_METRIC"]
              status_5xx_metric = os.environ["STATUS_5XX_METRIC"]

              s3_client = boto3.client("s3")
              cloudwatch = boto3.client('cloudwatch')

              try:
                  arrivals_file = s3_client.get_object(Bucket=bucket_name, Key=file_path)
                  arrivals_data = json.loads(arrivals_file['Body'].read())
              except Exception as e:
                  print(f"Error fetching raw S3 file: {e}")

                  cloudwatch.put_metric_data(
                      Namespace=cloudwatch_namespace,
                      MetricData=[
                          {
                              'MetricName': status_5xx_metric,
                              'Value': 1,
                              'Unit': 'Count'
                          }
                      ]
                  )

                  return {
                      'statusCode': 500,
                      'body': f"Failed to retrieve data from S3: {str(e)}"
                  }

              if isinstance(arrivals_data, dict):
                  arrivals_data = [arrivals_data]

              latest_arrivals_data = get_latest_journey_data(arrivals_data)

              metrics_sent = 0
              for trip_id, (timestamp, journey) in latest_arrivals_data.items():
                  delay_minutes = check_for_delay(journey)
                  route = journey.get("lineName", "244")
                  destination = journey.get("destinationName", "Unknown Destination")

                  # 1. Publish global, dimension-free Status_200 metric
                  cloudwatch.put_metric_data(
                      Namespace=cloudwatch_namespace,
                      MetricData=[
                          {
                              'MetricName': status_200_metric,
                              'Value': 1,
                              'Unit': 'Count'
                          }
                      ]
                  )

                  # 2. Publish detailed Status_200 metric with dimensions
                  cloudwatch.put_metric_data(
                      Namespace=cloudwatch_namespace,
                      MetricData=[
                          {
                              'MetricName': status_200_metric,
                              'Dimensions': [
                                  {'Name': 'Route', 'Value': route},
                                  {'Name': 'TripId', 'Value': trip_id}
                              ],
                              'Value': 1,
                              'Unit': 'Count'
                          }
                      ]
                  )

                  # 3. CRITICAL ADDITION: Publish ArrivalCount metric for the Bar Chart!
                  try:
                      cloudwatch.put_metric_data(
                          Namespace=cloudwatch_namespace,
                          MetricData=[
                              {
                                  'MetricName': 'ArrivalCount',
                                  'Dimensions': [
                                      {'Name': 'Route', 'Value': route},
                                      {'Name': 'Destination', 'Value': destination}
                                  ],
                                  'Value': 1.0,
                                  'Unit': 'Count'
                              }
                          ]
                      )
                  except Exception as e:
                      print(f"Error sending ArrivalCount metric: {e}")

                  # 4. Publish Delay metric
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
                          metrics_sent += 1
                      except Exception as e:
                          print(f"Error sending metric for TripId {trip_id}: {e}")

              return {
                  'statusCode': 200,
                  'body': f"Successfully updated {metrics_sent} metrics in CloudWatch."
              }
