import json
import io
import boto3

with open("./config/recognition_conf.json") as json_config_file:
    config = json.load(json_config_file)

control_session = boto3.Session(
    aws_access_key_id = config["aws"]["aws_access_key_id"],
    aws_secret_access_key = config["aws"]["aws_secret_access_key"],
    region_name = config["aws"]["region_name"]
)

s3_client_control = control_session.client('s3', region_name=config["aws"]["region_name"])

taskid = "vieraslajit_v2014_tie353_tieosa1"

bytes_buffer = io.BytesIO()
s3_key = taskid + "/" + taskid + "_metadata.json"
s3_client_control.download_fileobj(Bucket=config["recognition"]["layersapi_bucket"], Key=s3_key, Fileobj=bytes_buffer)
byte_value = bytes_buffer.getvalue()
str_value = byte_value.decode()

metadata_json = json.loads(str_value)

with open("./local_images/" + taskid + "/" + taskid + "_nometa.json", 'r') as f:
    result_json = json.load(f)


for i in result_json["recognition"]["image"]:
    print(i["imageurl"])

    for image_meta in metadata_json["data"]["getSearchFormImages"]:
        if (image_meta["awsTunnus"].split("/")[-1] == i["imageurl"]):
            print(image_meta)

            break

#result = list(filter(lambda fileName: (fileName == '353_1_5230_1_001.jpg'), metadata_json["data"]["getSearchFormImages"]))



# 353_1_5230_1_001.jpg




#    meta.awsTunnus.iloc[0].split("/")[-1] 