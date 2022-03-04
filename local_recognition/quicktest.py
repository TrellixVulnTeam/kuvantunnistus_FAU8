
from utility_functions import get_image_paths, get_queue, receive_messages, load_config, json_results
import json

detection_model, category_index = load_config()
print("Config load ok.")

searchid = "vieraslajit_v2014_tie4_tieosa425"
#searchid = "qa_search_1"

image_paths = get_image_paths("./local_images/" + searchid)

print("Running detection..")
result = json_results(detection_model, category_index, image_paths, 0.30, ["kurtturuusu"], searchid)

with open('./local_images/'+searchid+'/'+ searchid + '.json', 'w') as f:
  f.write(json.dumps(result))

print("done testing.")
