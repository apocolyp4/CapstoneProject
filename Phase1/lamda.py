AWSTemplateFormatVersion: '2010-09-09'
Description: S3 bucket + Lambda that fetches TfL arrivals and uploads JSON every 5 minutes

Resources:

  BronzeBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: zxdavebronze

  BronzeLambdaRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: bronze-lambda-role
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: BronzeLambdaS3Write
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:PutObject
                Resource: !Sub "arn:aws:s3:::${BronzeBucket}/*" # Fixed permission mismatch

  BronzeLambdaFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: bronze-lambda
      Handler: index.handler
      Runtime: python3.12
      Role: !GetAtt BronzeLambdaRole.Arn
      Timeout: 20
      Code:
        ZipFile: |
          import json
          import urllib.request
          import boto3

          URL = "https://api.tfl.gov.uk/Line/244/Arrivals"
          S3_BUCKET = "zxdavebronze"
          S3_KEY = "line_244_arrivals.json"

          s3 = boto3.client("s3")

          def handler(event, context):
              try:
                  # Fetch data from TfL API
                  with urllib.request.urlopen(URL, timeout=10) as response:
                      arrivals = json.loads(response.read().decode())

                  # Stream directly to S3 from memory (No /tmp file required)
                  s3.put_object(
                      Bucket=S3_BUCKET,
                      Key=S3_KEY,
                      Body=json.dumps(arrivals, indent=4),
                      ContentType="application/json"
                  )

                  return {
                      "status": "ok",
                      "uploaded_to": f"s3://{S3_BUCKET}/{S3_KEY}",
                      "count": len(arrivals)
                  }

              except Exception as e:
                  print(f"Error: {str(e)}") # Best practice: log errors to CloudWatch
                  raise e # Let Lambda system register the execution failure

  BronzeLambdaScheduleRule:
    Type: AWS::Events::Rule
    Properties:
      Name: bronze-lambda-schedule
      Description: Run the bronze Lambda every 5 minutes
      ScheduleExpression: rate(5 minutes)
      State: ENABLED
      Targets:
        - Arn: !GetAtt BronzeLambdaFunction.Arn
          Id: BronzeLambdaTarget

  BronzeLambdaInvokePermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref BronzeLambdaFunction
      Action: lambda:InvokeFunction
      Principal: events.amazonaws.com
      SourceArn: !GetAtt BronzeLambdaScheduleRule.Arn