#!/usr/bin/env python
# coding: utf-8

from queue import Empty
from sre_parse import FLAGS

from numpy import empty
from utility_functions import delete_message, get_image_paths, get_queue, receive_messages, load_config, json_results
import boto3
import botocore
import json
import time
import os
import glob
import pandas as pd
import io
from pyproj import Proj, transform

############## Main code

# Load config

with open("./config/recognition_conf.json") as json_config_file:
    config = json.load(json_config_file)

#### RECOGNITION WORKFLOW

# Start a session in AWS
control_session = boto3.Session(
    aws_access_key_id = config["aws"]["aws_access_key_id"],
    aws_secret_access_key = config["aws"]["aws_secret_access_key"],
    region_name = config["aws"]["region_name"]
)

image_session = boto3.Session(
    aws_access_key_id = config["images"]["aws_access_key_id"],
    aws_secret_access_key = config["images"]["aws_secret_access_key"],
    region_name = config["images"]["region_name"]
)

# Labels that this search engine supports
supported_labels = ['lupiini', 'kurtturuusu']

# Labels that are asked in the search task. This is gathered below from JSON.
task_labels = []

taskid = "vieraslajit_v2014_tie353_tieosa1"
localimagepath = '{}/{}/'.format(config["recognition"]["local_images_path"], taskid)

s3_client_control = control_session.client('s3', region_name=config["aws"]["region_name"])
s3_client_images = image_session.client('s3', region_name=config["images"]["region_name"])

sqs = control_session.resource('sqs', region_name = config["aws"]["region_name"])

# Check if there is tasks for us in queue

while True:

  recognition_queue = get_queue(sqs, config["recognition"]["sqs_queue"])
  tasks = receive_messages(recognition_queue, max_number=10, wait_time=0)

  t = time.localtime()
  current_time = time.strftime("%H:%M:%S", t)

  print(current_time + ": Found the queue and received " + str(len(tasks)) + " tasks")

  task_handled = False

  if len(tasks) > 0:
  # There are some tasks. Can we recognize these labels?

    for task_item in tasks:

      task_json = task_item.body

      task = json.loads(task_json)

      label_supported = False

      # Can we recognize any of the requested categories?
      for key, value in task["recognitiontask"].items(): 

        if key == "recognize" and any(label in supported_labels for label in value):

          task_labels = value
          print("One or more labels in the recognition task is supported by this recognition provider.")
          label_supported = True

        if label_supported and key == "imageurls" or key == "imageurlfile": 

          taskid = task["recognitiontask"]["taskid"]
          print("task id: " + taskid)

          localimagepath = '{}/{}/'.format(config["recognition"]["local_images_path"], taskid)

          min_score = task["recognitiontask"]["min_score"]

          print("Task requires " + str(min_score*100) + "% confidence.")

          # Create local folder for the search task
          try:
            os.mkdir(localimagepath)
            print("Local result directory " , localimagepath ,  " created") 
          except FileExistsError:
            print("Local directory " , localimagepath ,  " already exists")

          if key == "imageurls":

            imageurls_in_task = value

          elif key == "imageurlfile":

            bytes_buffer = io.BytesIO()
            s3_key = taskid + "/" + taskid + "_imagepaths.json"
            s3_client_control.download_fileobj(Bucket=config["recognition"]["layersapi_bucket"], Key=s3_key, Fileobj=bytes_buffer)
            byte_value = bytes_buffer.getvalue()
            str_value = byte_value.decode()

            imagepaths_json = json.loads(str_value)
            imageurls_in_task = imagepaths_json["imagepaths"]["imageurl"]

          for imageurl in imageurls_in_task:              
            bucketname = imageurl.split("/")[2]
            objectname = imageurl.replace("s3://"+bucketname+"/","")
            imagename = imageurl.split("/")[-1]

            s3_client_images.download_file(bucketname,objectname,localimagepath + imagename)
            print("Downloaded '" + imagename + "' from S3 to docker..")

          # RECOGNITION

          if label_supported:
            print('Loading recognition model from local file to memory... ', end='')
            start_time = time.time()

            detection_model, category_index = load_config() 

            end_time = time.time()
            elapsed_time = end_time - start_time
            print('Done! Took {} seconds'.format(round(elapsed_time,2)))

            # get local paths of images
            image_paths = get_image_paths(localimagepath)

            result_json = json_results(detection_model, category_index, image_paths, min_score, task_labels, taskid)

            # remove local images that have no search results
            recognized_image_list = []
            for i in result_json["recognition"]["image"]:
                recognized_image_list.append(i["imageurl"])

            image_files = glob.glob(localimagepath + "/*.jpg")

            print("We have " + str(len(image_files)) + " local image files from which " + str(len(recognized_image_list)) + " are recognized.")
            print("Removing unrecognized image files and uploading recognized to S3..")

            for fullpath in image_files:
              image_filename = fullpath.split("/")[-1]

              if image_filename not in recognized_image_list:
                os.remove(fullpath)
              else:
                s3_key = taskid + "/" + image_filename
              #  try:
                s3_client_control.upload_file(fullpath,config["recognition"]["layersapi_bucket"],s3_key)

                # make new file public
                s3_resource = control_session.resource('s3', region_name=config["aws"]["region_name"])
                object_acl = s3_resource.ObjectAcl(config["recognition"]["layersapi_bucket"], s3_key)
                object_acl.put(ACL='public-read')

                # remove also the local file when we are done
                os.remove(fullpath)

                #except botocore.exceptions.ClientError as e:
                #  raise

            print("Done with images")

            # upload search result to layersapi

            # Recognization results are in 'results'

            # - store the results in a tempfile
            result_string = json.dumps(result_json)

            with open(localimagepath + taskid + '_nometa.json', 'w') as nometa_json:
              nometa_json.write(result_string)

            #with open(localimagepath + taskid + '_nometa.json', 'r') as nometa_json:
            #  result_json = json.load(nometa_json)

            # Load metadata for all the analyzed images. This is retrieved in the lambda query step.

            bytes_buffer = io.BytesIO()
            s3_key = taskid + "/" + taskid + "_metadata.json"
            s3_client_control.download_fileobj(Bucket=config["recognition"]["layersapi_bucket"], Key=s3_key, Fileobj=bytes_buffer)
            byte_value = bytes_buffer.getvalue()
            str_value = byte_value.decode()

            metadata_json = json.loads(str_value)

            # - coordinate conversion

            inProj = Proj(init='epsg:3067')
            outProj = Proj(init='epsg:4326')

            # add imageurl items to list
            for i in result_json["recognition"]["image"]:
              #print(i["imageurl"])

              found_meta = Empty

              for image_meta in metadata_json["data"]["getSearchFormImages"]:
                if (image_meta["awsTunnus"].split("/")[-1] == i["imageurl"]):
                  found_meta = image_meta

                  x,y = transform(inProj,outProj,found_meta["xGivenCoord"],found_meta["yGivenCoord"])

                  i["lat"] = x
                  i["lon"] = y
                  i["date"] = found_meta["date"][:10]

                  break

              if found_meta == Empty:
                print("Metadata for image '" + i["imageurl"] + "' not found.")

            with open(localimagepath + "/" + taskid + ".json", "w") as f:
              json.dump(result_json, f)

            # Upload the regocnition with enriched metadata to S3

            s3_key = taskid + "/" + taskid + ".json"
            s3_resource = control_session.resource('s3', region_name=config["aws"]["region_name"])

            try:
              s3_resource.Object(config["recognition"]["layersapi_bucket"], s3_key).put(Body = json.dumps(result_json))

              # make new json-file public
              object_acl = s3_resource.ObjectAcl(config["recognition"]["layersapi_bucket"], s3_key)
              object_acl.put(ACL='public-read')

              task_handled = True

            except botocore.exceptions.ClientError as e:
              raise

            os.remove(localimagepath + taskid + '_nometa.json')
            os.remove(localimagepath + taskid + '.json')
            os.rmdir(localimagepath)
            print("Removed local directory " + localimagepath)

            if task_handled == True:
              delete_message(task_item)

  time.sleep(5) # sleep 5 seconds before polling the queue again

            

        

