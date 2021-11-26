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

sqs = control_session.resource('sqs', region_name = config["aws"]["region_name"])

# Check if there is tasks for us in queue

recognition_queue = get_queue(sqs, config["recognition"]["sqs_queue"])
tasks = receive_messages(recognition_queue, max_number=10, wait_time=0)

print("Found the queue and received " + str(len(tasks)) + " tasks")

if len(tasks) > 0:
  # There are some tasks. Can we recognize these labels?

  for task_item in tasks:

    task_json = task_item.body

    # HACK: load search string from local file as the SQS item is too small

    with open('search/vieraslajit_v2020_tie4_tieosa426_search.json', 'r') as file:
      task_json = file.read().replace('\n', '')
     
    task = json.loads(task_json)

    label_supported = False

    # Can we recognize any of the requested categories?
    for key, value in task["recognitiontask"].items(): 

      if key == "recognize" and any(label in supported_labels for label in value):

        task_labels = value
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
        s3 = image_session.client('s3', region_name=config["aws"]["region_name"])

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
    
      result = json_results(detection_model, category_index, image_paths, min_score, task_labels, taskid)

      #print(result)
      with open(localimagepath + taskid + '.json', 'w') as f:
        f.write(json.dumps(result))

      # should we delete the message from SQS?

