import requests
import json

query = """
{
getSearchFormImages(searchResults: {imageInfo: {road: "4", sourceSystem: "11", typeImage: "2"}, formSearch: true}, offset: 0, limit: 5000) {
    imageInfoId
    awsTunnus
    id
    road
    roadSection
    distance
    roadAddressDirection
    xCalcCoord
    yCalcCoord
    }
}"""

url = 'https://api.vaylapilvi.fi/ktv/api/graphql'
headers = {'content-type': 'application/json', 'x-api-key': 'jKUeMtRQD5KvHkJHkZgJPKUZnC0YEz37JXzyfsc'}

r = requests.post(url, json=json.dumps(query), headers=headers)

print(r.text)

