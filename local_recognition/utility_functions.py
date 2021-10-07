#!/usr/bin/env python
# coding: utf-8

import time
import os
import collections
import six
import tensorflow as tf
import pathlib
import logging
import boto3
import json
from botocore.exceptions import ClientError
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')   # Suppress Matplotlib warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
from object_detection.utils import label_map_util
from object_detection.utils import config_util
from object_detection.utils import visualization_utils as viz_utils
from object_detection.builders import model_builder
tf.get_logger().setLevel('ERROR')
tf.autograph.set_verbosity(0)

def load_config():
    path_to_labels = "./annotations/label_map.pbtxt"
    category_index = label_map_util.create_category_index_from_labelmap(path_to_labels,
                                                                        use_display_name=True)
    path_to_CFG = "./models/v2/efficientdet_d4_coco17_tpu-32/pipeline.config"
    path_to_CKPT = "./models/v2/efficientdet_d4_coco17_tpu-32/checkpoint" 

    #path_to_CFG = "./models/v1/efficientdet_d1_coco17_tpu-32/pipeline.config"
    #path_to_CKPT = "./models/v1/efficientdet_d1_coco17_tpu-32/checkpoint" 

    # Load pipeline config and build a detection model
    configs = config_util.get_configs_from_pipeline_file(path_to_CFG)
    model_config = configs['model']
    detection_model = model_builder.build(model_config=model_config, is_training=False)

    # Restore checkpoint
    ckpt = tf.compat.v2.train.Checkpoint(model=detection_model)
    ckpt.restore(os.path.join(path_to_CKPT, 'ckpt-0')).expect_partial()

    return detection_model, category_index

@tf.function
def detect_fn(detection_model, image):
    """Detect objects in image."""

    image, shapes = detection_model.preprocess(image)
    prediction_dict = detection_model.predict(image, shapes)
    detections = detection_model.postprocess(prediction_dict, shapes)

    return detections


def get_image_paths(path):
    image_paths =[]
    for filename in os.listdir(path):
        if not filename.endswith('.jpg'): continue
        fullname = os.path.join(path, filename)
        image_paths.append(fullname)
    return image_paths

def load_image_into_numpy_array(path):
    """Load an image from file into a numpy array.

    Puts image into numpy array to feed into tensorflow graph.
    Note that by convention we put it into a numpy array with shape
    (height, width, channels), where channels=3 for RGB.

    Args:
      path: the file path to the image

    Returns:
      uint8 numpy array with shape (img_height, img_width, 3)
    """
    return np.array(Image.open(path))


def plot_results(detection_model, category_index, image_paths):
    plt.rcParams["figure.figsize"] = (20,18)
    for image_path in image_paths:

        print('Running inference for {}... '.format(image_path), end='')

        image_np = load_image_into_numpy_array(image_path)

        # Things to try:
        # Flip horizontally
        # image_np = np.fliplr(image_np).copy()

        # Convert image to grayscale
        # image_np = np.tile(
        #     np.mean(image_np, 2, keepdims=True), (1, 1, 3)).astype(np.uint8)

        input_tensor = tf.convert_to_tensor(np.expand_dims(image_np, 0), dtype=tf.float32)

        detections = detect_fn(detection_model, input_tensor)

        # All outputs are batches tensors.
        # Convert to numpy arrays, and take index [0] to remove the batch dimension.
        # We're only interested in the first num_detections.
        num_detections = int(detections.pop('num_detections'))
        print(num_detections)
        detections = {key: value[0, :num_detections].numpy()
                      for key, value in detections.items()}
        detections['num_detections'] = num_detections
        # detection_classes should be ints.
        detections['detection_classes'] = detections['detection_classes'].astype(np.int64)
        label_id_offset = 1
        image_np_with_detections = image_np.copy()

        viz_utils.visualize_boxes_and_labels_on_image_array(
                image_np_with_detections,
                detections['detection_boxes'],
                detections['detection_classes']+label_id_offset,
                detections['detection_scores'],
                category_index,
                use_normalized_coordinates=True,
                max_boxes_to_draw=200,
                min_score_thresh=.30,
                agnostic_mode=False)
        plt.rcParams["figure.figsize"] = (20,18)
        plt.figure()
        plt.imshow(image_np_with_detections)
        print('Done')
        plt.show()

def logstring_of_boxes_and_labels_on_image_array(
    boxes,
    classes,
    scores,
    category_index,
    track_ids=None,
    use_normalized_coordinates=False,
    max_boxes_to_draw=20,
    min_score_thresh=.5):
  """Overlay labeled boxes on an image with formatted scores and label names.

  This function groups boxes that correspond to the same location
  and creates a display string for each detection and overlays these
  on the image. Note that this function modifies the image in place, and returns
  that same image.

  Args:
    image: uint8 numpy array with shape (img_height, img_width, 3)
    boxes: a numpy array of shape [N, 4]
    classes: a numpy array of shape [N]. Note that class indices are 1-based,
      and match the keys in the label map.
    scores: a numpy array of shape [N] or None.  If scores=None, then
      this function assumes that the boxes to be plotted are groundtruth
      boxes and plot all boxes as black with no classes or scores.
    category_index: a dict containing category dictionaries (each holding
      category index `id` and category name `name`) keyed by category indices.
    instance_masks: a uint8 numpy array of shape [N, image_height, image_width],
      can be None.
    instance_boundaries: a numpy array of shape [N, image_height, image_width]
      with values ranging between 0 and 1, can be None.
    keypoints: a numpy array of shape [N, num_keypoints, 2], can
      be None.
    keypoint_scores: a numpy array of shape [N, num_keypoints], can be None.
    keypoint_edges: A list of tuples with keypoint indices that specify which
      keypoints should be connected by an edge, e.g. [(0, 1), (2, 4)] draws
      edges from keypoint 0 to 1 and from keypoint 2 to 4.
    track_ids: a numpy array of shape [N] with unique track ids. If provided,
      color-coding of boxes will be determined by these ids, and not the class
      indices.
    use_normalized_coordinates: whether boxes is to be interpreted as
      normalized coordinates or not.
    max_boxes_to_draw: maximum number of boxes to visualize.  If None, draw
      all boxes.
    min_score_thresh: minimum score threshold for a box or keypoint to be
      visualized.
    agnostic_mode: boolean (default: False) controlling whether to evaluate in
      class-agnostic mode or not.  This mode will display scores but ignore
      classes.
    line_thickness: integer (default: 4) controlling line width of the boxes.
    mask_alpha: transparency value between 0 and 1 (default: 0.4).
    groundtruth_box_visualization_color: box color for visualizing groundtruth
      boxes
    skip_boxes: whether to skip the drawing of bounding boxes.
    skip_scores: whether to skip score when drawing a single detection
    skip_labels: whether to skip label when drawing a single detection
    skip_track_ids: whether to skip track id when drawing a single detection

  Returns:
    uint8 numpy array with shape (img_height, img_width, 3) with overlaid boxes.
  """
  # Create a display string (and color) for every box location, group any boxes
  # that correspond to the same location.
  box_to_display_str_map = collections.defaultdict(list)

  if not max_boxes_to_draw:
    max_boxes_to_draw = boxes.shape[0]

  for i in range(boxes.shape[0]):

    if scores is None or scores[i] > min_score_thresh:
      box = tuple(boxes[i].tolist())

      if scores is not None:
        display_str = ''
        if classes[i] in six.viewkeys(category_index):
            class_name = category_index[classes[i]]['name']
        else:
            class_name = 'N/A'
        display_str = str(class_name)
        
        if not display_str:
            display_str = '{}%'.format(round(100*scores[i]))
        else:
            display_str = '{}: {}%'.format(display_str, round(100*scores[i]))
        box_to_display_str_map[box].append(display_str)

        if track_ids is not None:
          if not display_str:
            display_str = 'ID {}'.format(track_ids[i])
          else:
            display_str = '{}: ID {}'.format(display_str, track_ids[i])

        box_to_display_str_map[box].append(display_str)

  # Draw all boxes onto image.
  #for box, color in box_to_color_map.items():
 
  return box_to_display_str_map


def log_results(detection_model, category_index, image_paths):

    timestr = time.strftime("%Y%m%d-%H%M%S")
    logfilename = "batchblur_" + timestr + ".csv"

    # logfile = open(os.path.join(output_path, "batchblur_" + timestr + ".csv"), "a")#

    print('Creating a log file {}... '.format(logfilename), end='')

    for image_path in image_paths:

        image_np = load_image_into_numpy_array(image_path)

        input_tensor = tf.convert_to_tensor(np.expand_dims(image_np, 0), dtype=tf.float32)

        detections = detect_fn(detection_model, input_tensor)

        # All outputs are batches tensors.
        # Convert to numpy arrays, and take index [0] to remove the batch dimension.
        # We're only interested in the first num_detections.
        num_detections = int(detections.pop('num_detections'))
        print(num_detections)
        detections = {key: value[0, :num_detections].numpy()
                      for key, value in detections.items()}
        detections['num_detections'] = num_detections
        # detection_classes should be ints.
        detections['detection_classes'] = detections['detection_classes'].astype(np.int64)
        label_id_offset = 1

        print('Logging inference for {}... '.format(image_path), end='')

        min_score_thresh=.35
        boxes = detections['detection_boxes']
        classes = detections['detection_classes']+label_id_offset
        scores = detections['detection_scores']

        for i in range(boxes.shape[0]):

            if scores[i] > min_score_thresh:

                if classes[i] in six.viewkeys(category_index):
                    class_name = str(category_index[classes[i]]['name'])
                else:
                    class_name = 'N/A'
        
                score = round(100*scores[i])

                box = tuple(boxes[i].tolist())
                ymin, xmin, ymax, xmax = box

                log_string = '{},{},{},{},{},{},{}'.format(image_path, class_name, score, ymin, xmin, ymax, xmax)
            
                print(log_string)

        print('Done')

def json_results(detection_model, category_index, image_paths, min_score_thresh, search_labels):

  # do we need timestamp in json?
  #timestr = time.strftime("%Y%m%d-%H%M%S")

  print(search_labels)

  json_result = json.loads('{"recognition":{"image": []}}')

  for image_path in image_paths:

      image_np = load_image_into_numpy_array(image_path)

      input_tensor = tf.convert_to_tensor(np.expand_dims(image_np, 0), dtype=tf.float32)

      detections = detect_fn(detection_model, input_tensor)

      # All outputs are batches tensors.
      # Convert to numpy arrays, and take index [0] to remove the batch dimension.

      num_detections = int(detections.pop('num_detections'))
      detections = {key: value[0, :num_detections].numpy()
                    for key, value in detections.items()}
      detections['num_detections'] = num_detections

      # detection_classes should be ints.
      detections['detection_classes'] = detections['detection_classes'].astype(np.int64)
      label_id_offset = 1

      print('Running detection for {}... '.format(image_path))

      boxes = detections['detection_boxes']
      classes = detections['detection_classes']+label_id_offset
      scores = detections['detection_scores']

      image_block = json.loads('{"imageurl": "", "results": []}')

      # keep only the filename
      image_block["imageurl"] = image_path.split("/")[-1]

      results_found = False

      for i in range(boxes.shape[0]):

          if scores[i] > min_score_thresh:

              if classes[i] in six.viewkeys(category_index):
                  class_name = str(category_index[classes[i]]['name'])
              else:
                  class_name = 'N/A'

              if search_labels == None or class_name in search_labels:

                score = round(100*scores[i])
                box = tuple(boxes[i].tolist())
                ymin, xmin, ymax, xmax = box

                result_block = json.loads('{"label": "", "probability": "","x_min": "", "y_min": "", "x_max": "", "y_max": "" }')
                result_block["label"] = class_name
                result_block["probability"] = score
                result_block["y_min"] = ymin
                result_block["x_min"] = xmin
                result_block["y_max"] = ymax
                result_block["x_max"] = xmax

                image_block["results"].append(result_block)
                results_found = True
                        
      # Add recognition results
      if results_found == True:
        json_result["recognition"]["image"].append(image_block)

  return json_result


################ QUEUE FUNCTIONS

logger = logging.getLogger(__name__)

def get_queue(sqs, name):
    """
    Gets an SQS queue by name.

    :param name: The name that was used to create the queue.
    :return: A Queue object.
    """
    try:
        queue = sqs.get_queue_by_name(QueueName=name)
        logger.info("Got queue '%s' with URL=%s", name, queue.url)
    except ClientError as error:
        logger.exception("Couldn't get queue named %s.", name)
        raise error
    else:
        return queue

def receive_messages(queue, max_number, wait_time):
    """
    Receive a batch of messages in a single request from an SQS queue.

    Usage is shown in usage_demo at the end of this module.

    :param queue: The queue from which to receive messages.
    :param max_number: The maximum number of messages to receive. The actual number
                       of messages received might be less.
    :param wait_time: The maximum time to wait (in seconds) before returning. When
                      this number is greater than zero, long polling is used. This
                      can result in reduced costs and fewer false empty responses.
    :return: The list of Message objects received. These each contain the body
             of the message and metadata and custom attributes.
    """
    try:
        messages = queue.receive_messages(
            MessageAttributeNames=['All'],
            MaxNumberOfMessages=max_number,
            WaitTimeSeconds=wait_time
        )
        for msg in messages:
            logger.info("Received message: %s: %s", msg.message_id, msg.body)
    except ClientError as error:
        logger.exception("Couldn't receive messages from queue: %s", queue)
        raise error
    else:
        return messages

def delete_message(message):
    """
    Delete a message from a queue. Clients must delete messages after they
    are received and processed to remove them from the queue.

    :param message: The message to delete. The message's queue URL is contained in
                    the message's metadata.
    :return: None
    """
    try:
        message.delete()
        logger.info("Deleted message: %s", message.message_id)
    except ClientError as error:
        logger.exception("Couldn't delete message: %s", message.message_id)
        raise error

