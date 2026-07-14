import json
import boto3

file_name = "aws_credentials.json"

#Load the credentials from a JSON file so I can keep them out of the code and make sure they are not pushed to GitHub
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


s3_client = boto3.client(client_type , aws_access_key_id = access_key,  aws_secret_access_key = secret_key, region_name = region)
cloudwatch = boto3.client('cloudwatch', aws_access_key_id = access_key, aws_secret_access_key = secret_key, region_name = region)

arrivials_file = s3_client.get_object(Bucket=bucket_name, Key=file_path)
arrivials = json.loads(arrivials_file['Body'].read())

print(arrivials)

print("S3 Client created successfully")
