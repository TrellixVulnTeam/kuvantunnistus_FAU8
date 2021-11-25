import os
import glob
import json

searchid = "vieraslajit_v2020_tie4_tieosa425"

imagefolder = "../local_images/"

json_result_file = imagefolder + searchid + "/" + searchid + ".json"

with open(json_result_file, "rb") as infile:
    json_result = json.load(infile)

# add imageurl items to list
url_list = []
for i in json_result["recognition"]["image"]:
    url_list.append(i["imageurl"])

image_files = glob.glob(imagefolder + searchid + "/*.jpg")

for fullpath in image_files:
    f = fullpath.split("/")[-1]
    if f not in url_list:
        os.remove(fullpath)

