#!/usr/bin/env python
# coding: utf-8

from utility_functions import get_image_paths, get_queue, receive_messages, load_config, json_results
import boto3
import json
import time
import os

############## Main code

# Load config

with open("../../configuration/recognition_conf.json") as json_config_file:
    config = json.load(json_config_file)

#### RECOGNITION WORKFLOW

# Start a session in AWS
session = boto3.Session(
    aws_access_key_id = config["aws"]["aws_access_key_id"],
    aws_secret_access_key = config["aws"]["aws_secret_access_key"],
    region_name = config["aws"]["region_name"]
)

#TODO: put this to config
supported_labels = ["lupiini", "kurtturuusu"]

sqs = session.resource('sqs', region_name = config["aws"]["region_name"])

# Check if there is tasks for us in queue

#TODO: put queue name in config
recognition_queue = get_queue(sqs, config["recognition"]["sqs_queue"])
tasks = receive_messages(recognition_queue, max_number=10, wait_time=0)

print("Found the queue and received " + str(len(tasks)) + " tasks")

if len(tasks) > 0:
  # There are some tasks. Can we recognize these labels?

  for task_item in tasks:

    task_json = task_item.body

    task = json.loads(task_json)

    label_supported = False

    # Can we recognize any of the requested categories?
    for key, value in task["recognitiontask"].items(): 

      if key == "recognize" and any(label in supported_labels for label in value):
        #for label in value.items():
        # if label in supported_labels:
        # Yes, we know this category. Handle the task..
        print("One or more labels in the recognition task is supported by this recognition provider.")
        label_supported = True

      if label_supported and key == "imageurls": 

        taskid = task["recognitiontask"]["taskid"]
        localimagepath = '{}/{}/'.format(config["recognition"]["local_images_path"], taskid)

        min_score = task["recognitiontask"]["min_score"]

        print("Task requires " + str(min_score*100) + "% confidence.")

        # Create local folder for the search task
        try:
          os.mkdir(localimagepath)
          print("Local result directory " , localimagepath ,  " created") 
        except FileExistsError:
          print("Local directory " , localimagepath ,  " already exists")

        # - download locally the image from S3
        s3 = session.client('s3', region_name="eu-west-1")

        for imageurl in value:              
          bucketname = imageurl.split("/")[2]
          objectname = imageurl.replace("s3://"+bucketname+"/","")
          imagename = imageurl.split("/")[-1]

          s3.download_file(bucketname,objectname,localimagepath + imagename)

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
    
      result = json_results(detection_model, category_index, image_paths, min_score)

      #print(result)
      with open(localimagepath + taskid + '.json', 'w') as f:
        f.write(json.dumps(result))

      # should we delete the message from SQS?

