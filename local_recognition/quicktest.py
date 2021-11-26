
from utility_functions import get_image_paths, get_queue, receive_messages, load_config, json_results
import json

detection_model, category_index = load_config()
print("Config load ok.")
image_paths = get_image_paths("./local_images/vieraslajit_tie4_tieosa425")

print("Running detection..")
result = json_results(detection_model, category_index, image_paths, 0.22, ["lupiini"])

with open('./local_images/vieraslajit_tie4_tieosa425/vieraslajit_tie4_tieosa425.json', 'w') as f:
  f.write(json.dumps(result))

print("done testing.")
