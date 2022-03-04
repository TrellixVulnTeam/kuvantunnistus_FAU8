import json
import pandas as pd

searchid = "vieraslajit_v2014_tie4_tieosa425"

imagefolder = "../local_images/"
#metafolder = "./search_v2/"
metafolder = "./"

json_result_file = imagefolder + searchid + "/" + searchid + ".json"
json_meta_file = metafolder + searchid + "_metadata.json"

with open(json_result_file, "rb") as infile:
    json_result = json.load(infile)

with open(json_meta_file, "rb") as infile:
    json_meta = json.load(infile)

meta = pd.json_normalize(json_meta["metadata"]["image"])

# add imageurl items to list
for i in json_result["recognition"]["image"]:
    image_meta = meta[meta.imageurl == i["imageurl"]]

    if (not image_meta.empty):
        i["date"] = image_meta.date.iloc[0]
        i["lat"] = image_meta.lat.iloc[0]
        i["lon"] = image_meta.lon.iloc[0]
    else:
        print("Metadata for image '" + i["imageurl"] + "' not found.")

with open(imagefolder + searchid + "/" + searchid + "_withmeta.json", "w") as f:
    json.dump(json_result, f)



 