import os
import glob
import json
import pandas as pd
import pandas.io.json as pdj

searchid = "vieraslajit_v2020_tie4_tieosa425"

imagefolder = "../local_images/"
metafolder = "./"

json_result_file = imagefolder + searchid + "/" + searchid + ".json"
json_meta_file = metafolder + searchid + "_metadata.json"

with open(json_result_file, "rb") as infile:
    json_result = json.load(infile)

with open(json_meta_file, "rb") as infile:
    json_meta = json.load(infile)

meta = pdj.json_normalize(json_meta["metadata"]["image"])

# add imageurl items to list
for i in json_result["recognition"]["image"]:
    image_meta = meta[meta.imageurl == i["imageurl"]] 
    i["lat"] = image_meta.lat.values[0]
    i["lon"] = image_meta.lon.values[0]

with open(imagefolder + searchid + "/" + searchid + "_withmeta.json", "w") as f:
    json.dump(json_result, f)



 