import requests
import json
import boto3

def GetImageMetadata(road, roadsection_start, roadsection_end, start_time, end_time):
    query = """
    {
      "operationName": "getSearchFormImages",
      "variables": {
        "searchResults": {
          "imageInfo": {
            "sourceSystem": "11",
            "typeImage": "2",
            "fileName": null,
            "road": \"""" + str(road) + """\",
            "trackCode": null,
            "municipality": null,
            "region": null,
            "ely": null,
            "contractArea": null,
            "track": null,
            "imagingJobId": null,
            "displayType": 1
          },
          "keyWords": "",
          "tags": null,
          "startTime": \"""" + str(start_time) + """\",
          "endTime": \"""" + str(end_time) + """\",
          "formSearch": true,
          "roadSectionStart": \"""" + str(roadsection_start) + """\",
          "roadSectionEnd": \"""" + str(roadsection_end) + """\",
          "distanceStart": "",
          "distanceEnd": "",
          "latestImage": null,
          "fileType": null,
          "historyData": true,
          "roleSalainen": false
        },
        "offset": 0
      },
      "query": "fragment ImageInfoFields on GQLImageInfo {\n imageInfoId: imageInfoId\n imageId: imageId\n historyDate: historyDate\n fileName: fileName\n id: id\n typeImage: typeImage\n sourceSystem: sourceSystem\n ely: ely\n municipality: municipality\n region: region\n contractArea: contractArea\n road: road\n roadSection: roadSection\n distance: distance\n trackCode: trackCode\n givenCoord: givenCoord\n xGivenCoord: xGivenCoord\n yGivenCoord: yGivenCoord\n zGivenCoord: zGivenCoord\n calcCoord: calcCoord\n xCalcCoord: xCalcCoord\n yCalcCoord: yCalcCoord\n zCalcCoord: zCalcCoord\n definition: definition\n roadAddressDirection: roadAddressDirection\n descDirection: descDirection\n side: side\n getMovedCenterLine: getMovedCenterLine\n date: date\n publicity: publicity\n organization: organization\n lastName: lastName\n firstName: firstName\n trTerminationDate: trTerminationDate\n trChanges: trChanges\n prStatus: prStatus\n prComplete: prComplete\n vkmStatus: vkmStatus\n trStatus: trStatus\n userCreator: userCreator\n addedDate: addedDate\n userChange: userChange\n changeDate: changeDate\n tlnumber: tlnumber\n mainImage: mainImage\n track: gqlTrack {\n trackId: trackId\n trackObjId: trackObjId\n trackNumber: trackNumber\n trackLocation: trackLocation\n kilometer: kilometer\n meter: meter\n kilometerStart: kilometerStart\n kilometerEnd: kilometerEnd\n meterStart: meterStart\n meterEnd: meterEnd\n __typename\n }\n awsTunnus: awsTunnus\n awsUrl: awsUrl\n awsThumbnailUrl: awsThumbnailUrl\n awsPictureUrl: awsPictureUrl\n imagingJobId: imagingJobId\n displayType: displayType\n stationId: stationId\n stationName: stationName\n greenBridgeId: greenBridgeId\n greenBridgeName: greenBridgeName\n sillariBridgeId: sillariBridgeId\n sillariBridgeName: sillariBridgeName\n __typename\n}\n\nquery getSearchFormImages($searchResults: SearchResults!, $limit: Int, $offset: Int) {\n getSearchFormImages(\n searchResults: $searchResults\n limit: $limit\n offset: $offset\n ) {\n ...ImageInfoFields\n __typename\n }\n}\n"
    }
    """
    
    url = 'https://api.vaylapilvi.fi/ktv/api/graphql'
    headers = {'content-type': 'application/json', 'x-api-key': 'ojKUeMtRQD5KvHkJHkZgJPKUZnC0YEz37JXzyfsc'}
    
    r = requests.post(url, data=query, headers=headers)

    try:
        json_result = json.loads(r.text)
    except:
        print("QUERY: " + query)
        print("ERROR: " + r.text)
        json_result = -1

    return json_result


def lambda_handler(event, context):
    
    with open("./config/recognition_conf.json") as json_config_file:
        config = json.load(json_config_file)


    road = event['road'] # "353"
    roadsection_start = event['roadsection_start'] # "1"
    roadsection_end = event['roadsection_end'] # "1"

    start_time = event['start_time'] # "1.1.2014"
    end_time = event['end_time'] #1.11.2015"

    searchid = "vieraslajit_v" + start_time.split(".")[-1] + "_" + end_time.split(".")[-1] + "_tie" + road + "_tieosa" + roadsection_start + "_" + roadsection_end

    metaresult = GetImageMetadata(road, roadsection_start, roadsection_end, start_time, end_time)

    if (metaresult != "-1"):

        print("Query resulted " + str(len(metaresult["data"]["getSearchFormImages"])) + " images for analysis.") 

        # Start building a recognition task
        task = json.loads('{"recognitiontask": {"taskid": "","recognize": ["kurtturuusu","lupiini"],"imageurlfile": "S3 path","max_boxes": 10,"min_score": 0.30}}')
        task["recognitiontask"]["taskid"] = searchid

        imagepath_json = json.loads('{"imagepaths": {"taskid": "","imageurl": []}}')
        
        for i in metaresult["data"]["getSearchFormImages"]:
            s3path = "s3://kuvatietovarasto-prod/picture/" + i["awsTunnus"]
            imagepath_json["imagepaths"]["imageurl"].append(s3path)

        imagepath_json["imagepaths"]["taskid"] = searchid

        with open("./tmp/" + searchid + "_imagepaths.json", "w") as f:
            json.dump(imagepath_json, f)

        
        control_session = boto3.Session(
            aws_access_key_id = config["aws"]["aws_access_key_id"],
            aws_secret_access_key = config["aws"]["aws_secret_access_key"],
            region_name = config["aws"]["region_name"])
        
        s3_client_control = control_session.client('s3', region_name=config["aws"]["region_name"])

        # METADATA

        with open("./tmp/" + searchid + "_metadata.json", "w") as f:
            json.dump(metaresult, f)

        s3_key = searchid + "/" + searchid + "_metadata.json"
        s3_client_control.upload_file("./tmp/" + searchid + "_metadata.json",config["recognition"]["layersapi_bucket"],s3_key)

        # IMAGE PATHS

        s3_key = searchid + "/" + searchid + "_imagepaths.json"
        s3_client_control.upload_file("./tmp/" + searchid + "_imagepaths.json",config["recognition"]["layersapi_bucket"],s3_key)

        print("Done uploading the image path file to " + config["recognition"]["layersapi_bucket"] + s3_key)

        # SEARCH TASK

        # - insert path of image url list to task 
        task["recognitiontask"]["imageurlfile"] = s3_key

        # - store task to S3
        with open("./tmp/" + searchid + "_search.json", "w") as f:
            json.dump(task, f)

        s3_key = searchid + "/" + searchid + "_search.json"
        s3_client_control.upload_file("./tmp/" + searchid + "_search.json",config["recognition"]["layersapi_bucket"],s3_key)

        print("Inserted the image path file to " + config["recognition"]["layersapi_bucket"] + "/" + s3_key)

        # - send task to SQS
        # - dump search task to string
        task_string = json.dumps(task)

        sqs_resource = control_session.resource('sqs', region_name = config["aws"]["region_name"])
        sqs_client = control_session.client('sqs', region_name = config["aws"]["region_name"])

        response = sqs_client.get_queue_url(QueueName=config["recognition"]["sqs_queue"])
        queue_url = response["QueueUrl"]

        response = sqs_client.send_message(
            QueueUrl=queue_url,
            DelaySeconds=5,
            MessageBody=task_string)

        return {
            'status': 0
        }
