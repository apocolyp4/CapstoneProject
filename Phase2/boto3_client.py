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


client_type = credentials['client_type']
access_key = credentials['access_key']
secret_key = credentials['secret_key']
region = credentials['region']



#s3_client = boto3.client(client_type, aws_access_key_id = access_key,  aws_secret_access_key = secret_key, region_name = region)


#cloudwatch = boto3.client('cloudwatch')

print("S3 Client created successfully")
