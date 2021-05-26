# rokuweather
Weather display for Roku Soundbridge devices using Yahoo Weather API

Installation of __python3__ and __python3-requests__ library is required.
```
Usage:
  rokuweather [opts] RokuSB

Hostname or IP of RokuSB required argument

Command-line opts:

  -h, --help      This text
  -v, --verbose   Turn on debug output
  -l, --location  Location (City,State,Country or zip-code), Default: "Boston,MA,US"
  -u, --units     Units of measurement (Standard, Metric or Imperial)
  -t, --type      Display type (1 := M1000/1, 2 := R1000)
  -r, --reset     Reset Soundbridge and exit sketch
```

Example:

`$ ./rokuweather.py -l "Watertown,MA,US" 192.168.123.445`
