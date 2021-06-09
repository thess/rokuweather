# rokuweather
Weather display for Roku Soundbridge devices using OpenweatherMaps API

Installation of __python3__,  __python3-json__ and __python3-requests__ is required.
```
Usage:
  rokuweather [opts] RokuSB

Hostname or IP of RokuSB required argument

Command-line opts (override config):

  -h, --help      This text
  -v, --verbose   Turn on debug output
  -l, --location  Location (City,State,Country or zip-code), Default: "Boston,MA,US"
  -u, --units     Units of measurement (Standard, Metric or Imperial)
  -t, --type      Display type (1 := M1000/1, 2 := R1000)
  -r, --reset     Reset Soundbridge and exit sketch
```

OpenWeather API credentials, location and units may be stored in __ow_data.py__

* Application credentials for OpenWeather API (required)
* Either 'location' or 'lat' and 'lon' must be supplied
* Location may be specified as zip-code. Country code is optional

Example of __ow_data.py__ contents:
```
config = dict(
    appid = "<supply-your-own>",
    location = "Boston,MA,US",
    units = "Imperial",
    #lat = "",
    #lon = "",
)
```
Example:

`$ ./rokuweather.py -l "Watertown,MA,US" 192.168.123.445`
