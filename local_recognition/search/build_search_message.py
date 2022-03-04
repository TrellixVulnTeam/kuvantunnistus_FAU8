import json
import glob
from pyproj import Proj, transform

read_files = glob.glob("./REST-results/LAP_Kemi_v2014_4_424/*.json")

searchid = "vieraslajit_v2014_tie4_tieosa424"

task = json.loads('{"recognitiontask": {"taskid": "","recognize": ["kurtturuusu","lupiini"],"imageurls": [],"max_boxes": 10,"min_score": 0.30}}')
imeta = json.loads('{"metadata": {"image": []}}')

image_s3_paths = []
image_xc = []
image_yc = []

inProj = Proj(init='epsg:3067')
outProj = Proj(init='epsg:4326')

for f in read_files:
    with open(f, "rb") as infile:
        results = json.load(infile)

        for i in results:
            #print(i["awsTunnus"])
            s3path = "s3://kuvatietovarasto-prod/picture/" + i["awsTunnus"]
            task["recognitiontask"]["imageurls"].append(s3path)

            imeta_block = json.loads('{"imageurl": "","xcoord": 0,"ycoord": 0,"lat":0, "lon":0, "date":""}')
            imeta_block["imageurl"] = s3path.split("/")[-1]
            imeta_block["xcoord"] = i["xGivenCoord"]
            imeta_block["ycoord"] = i["yGivenCoord"]

            x,y = transform(inProj,outProj,i["xGivenCoord"],i["yGivenCoord"])

            imeta_block["lat"] = y
            imeta_block["lon"] = x

            imeta_block["date"] = i["date"][:10]

            imeta["metadata"]["image"].append(imeta_block)

task["recognitiontask"]["taskid"] = searchid

with open("./" + searchid + "_search.json", "w") as f:
    json.dump(task, f)

with open("./" + searchid + "_metadata.json", "w") as f:
    json.dump(imeta, f)
