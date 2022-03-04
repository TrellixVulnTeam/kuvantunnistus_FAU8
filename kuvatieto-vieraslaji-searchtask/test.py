from lambda_function import lambda_handler

event = {
  "road": "353",
  "roadsection_start": "1",
  "roadsection_end": "1",
  "start_time": "1.1.2014",
  "end_time": "1.1.2015"
}

lambda_handler(event, 1)
