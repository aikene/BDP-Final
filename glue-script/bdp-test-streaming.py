import sys
import datetime
import boto3
import base64
from pyspark.sql import DataFrame, Row
from pyspark.context import SparkContext
from pyspark.sql.types import *
from pyspark.sql.functions import *
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue import DynamicFrame

args = getResolvedOptions(sys.argv, \
                          ['JOB_NAME', \
                           'aws_region', \
                           'output_path'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# S3 sink locations
aws_region = args['aws_region']
output_path = args['output_path']

s3_target = output_path
checkpoint_location = output_path + "cp/"
temp_path = output_path + "temp/"

print("*** HERE ***")
print(f"S3 TARGET {s3_target}")
print(f"CHECKPOINT LOCATION {checkpoint_location}")
print(f"TEMP_PATH {temp_path}")

def processBatch(data_frame, batchId):
    print("*** DATA FRAME SCHEMA ***")
    data_frame.printSchema()

    now = datetime.datetime.now()
    year = now.year
    month = now.month
    day = now.day
    hour = now.hour
    minute = now.minute
    if (data_frame.count() > 0):
        dynamic_frame = DynamicFrame.fromDF(data_frame, glueContext, "from_data_frame")
        print("*** DYNAMIC FRAME SCHEMA ***")
        dynamic_frame.printSchema()

        # Write to S3 Sink
        # s3path = s3_target + "/ingest_year=" + "{:0>4}".format(str(year)) + "/ingest_month=" + "{:0>2}".format(str(month)) + "/ingest_day=" + "{:0>2}".format(str(day)) + "/ingest_hour=" + "{:0>2}".format(str(hour)) + "/"
        s3path = s3_target + "/stoinks"
        s3sink = glueContext.write_dynamic_frame.from_options(
            frame = dynamic_frame, connection_type = "s3",
            connection_options = {"path": s3path},
            format = "parquet",
            transformation_ctx = "s3sink"
        )

# Read from Kinesis Data Stream
kinesis_options = {
    "streamARN": "",
    "startingPosition": "TRIM_HORIZON",
    "inferSchema": "true",
    "classification": "json"
}
sourceData = glueContext.create_data_frame.from_options(connection_type="kinesis", connection_options=kinesis_options)
print("KINESIS DATA STREAM SCHEMA")
sourceData.printSchema()

glueContext.forEachBatch(
    frame = sourceData,
    batch_function = processBatch,
    options = {
        "windowSize": "100 seconds",
        "checkpointLocation": "s3://big-data-88-processing/final-ouput-path/checkpoint/"
    }
)
job.commit()
