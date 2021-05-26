#!/usr/bin/env python3

"""rokuweather [opts] RokuSB

Hostname or IP of RokuSB required argument

Command-line opts:

-h, --help      This text
-v, --verbose   Turn on debug output
-l, --location  Location (City,State,Country) Default: "Boston,MA,US"
-u, --units     Units of measurement (Standard, Metric or Imperial)
-t, --type      Display type (1 := M1000/1, 2 := R1000)
-r, --reset     Reset Soundbridge and exit sketch

"""
import sys, traceback
import time
import getopt
import requests
import json

import roku_tn
from draw_icon import wi_icons

# OpenWeather API credentials (supply your own)
from ow_data import config

# Example file ow_data.py contents
# Application credentials for OpenWeather API
# Either 'location' or 'lat' and 'lon' must be supplied
# Location may be specified as zip-code. Country code is optional
#config = dict(
#    appid = "",
#    location = "Boston,MA,US",
#    units = "Imperial",
#    #lat = "",
#    #lon = "",
# )


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def main(argv=None):
    # Some constant defs
    getowdata = "Getting weather data from OpenWeather..."
    ow_appid = config['appid']
    try:
        ow_lat = config['lat']
        ow_lon = config['lon']
    except KeyError:
        ow_lat = ow_lon = None
        pass

    ow_url = "https://api.openweathermap.org/data/2.5/onecall"
    ow_url_current = "https://api.openweathermap.org/data/2.5/weather"
    try:
        location = config['location']
    except KeyError:
        location = None
        pass

    wind_vector = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                   'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    # Type 1 := 280x16, 2 := 280x32
    display_type = 1
    sb_open = False

    # Single panel display time
    panel_delay = 10

    # Parse any command-line args
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hvl:t:ru:", ["help", "verbose", "location=", "type=", "reset", "units="])
        except getopt.error as msg:
            raise Usage(msg)

        # Gather command options
        debug_output = False
        reset_sb = False
        units = None
        for o, v in opts:
            if (o == '-v'):
                debug_output = True
            if (o in ["-h", "--help"]):
                print(__doc__)
                return
            if (o in ["-l", "--location"]):
                location = v
            if (o in ["-t", "--type"]):
                display_type = v
            if (o in ["-r", "--reset"]):
                reset_sb = True
            if (o in ["-u", "--units"]):
                units = v.lower()

        if units is None:
            units = 'imperial'

        if units == 'imperial':
            temp_units = 'F'
            speed_units = 'mph'
        elif units == 'metric':
            temp_units = 'C'
            speed_units = 'm/s'
        else:
            temp_units ='K'
            speed_units = 'm/s'

        # Remaining arg is display host
        if (len(args) != 1):
            raise Usage("Display host name or IP required")

        sb_host = args[0]

        # Local display panel functions
        def current_conditions(sb):
            # Roku current weather to display
            fnt = 1 if (sb.dpytype == 1) else 2
            xoff = 80 if (sb.dpytype == 1) else 90
            sb.msg(text="{}\xb0{}".format(ctemp, temp_units), font=10 if (sb.dpytype == 1) else 3, x=34, y=0, clear=True)
            sb.msg(text="{}, Humidity: {}%".format(cdescr, humidity), font=fnt, x=xoff, y=0)
            sb.msg(text="Wind: {} at {}{}, Chill: {}\xb0{}".format(wvector, wspeed, speed_units, wchill, temp_units),
                                                                font=fnt, x=xoff, y=8 if (sb.dpytype == 1) else 16)
            icon_map.drawItAt(sb, ccode, 0, 0)
            return True

        def weather_preview(sb):
            # Roku weather preview to display
            #  rest of today
            fnt = 1 if (sb.dpytype == 1) else 2
            ymax = 15 if (sb.dpytype == 1) else 31
            yoff = 8 if (sb.dpytype == 1) else 16
            sb.msg(text=today_day, font=fnt, x=0, y=0, clear=True)  # day
            sb.msg(text=today_date, x=0, y=yoff)  # date
            sb.msg(text="{}\xb0{}".format(today_high, temp_units), x=82, y=0)  # max temp
            sb.msg(text="{}\xb0{}".format(today_low, temp_units), x=82, y=yoff)  # min temp
            # Clear second half and  draw border line
            sb.cmd("sketch -c color 0")
            sb.cmd("sketch -c rect 139 0 141 {}".format(ymax))
            sb.cmd("sketch -c color 1")
            sb.cmd("sketch -c line 140 0 140 {}".format(ymax))
            # tomorrow
            xoff = 227 if (sb.dpytype == 1) else 233
            sb.msg(text=tomorrow_day, font=fnt, x=145, y=0)  # day
            sb.msg(text=tomorrow_date, x=145, y=yoff)  # date
            sb.msg(text="{}\xb0{}".format(tomorrow_high, temp_units), x=xoff, y=0)  # max temp
            sb.msg(text="{}\xb0{}".format(tomorrow_low, temp_units), x=xoff, y=yoff)  # min temp

            icon_map.drawItAt(sb, today_code, 47 if (sb.dpytype == 1) else 49, 0)
            icon_map.drawItAt(sb, tomorrow_code, 188 if (sb.dpytype == 1) else 194, 0)
            return True

        def local_datetime(sb):
            sb.msg(text=time.strftime('%H:%M   %A, %b %-d'),
                   clear=True, font=10 if (sb.dpytype == 1) else 2, x=60, y=0)
            return True if (sb.dpytype == 1) else False

        def sun_rise_set(sb):
            fnt = 10 if (sb.dpytype == 1) else 2
            yoff = 0 if (sb.dpytype == 1) else 16
            sb.msg(text="Sunrise: " + sunrise, font=fnt, x=8, y=yoff, clear=True if (sb.dpytype == 1) else False)
            sb.msg(text="Sunset: " + sunset, font=fnt, x=148, y=yoff)
            return True

        def openweather_error(sb, etext, ecode):
            sb.msg(text=etext.format(ecode), clear=True, font=1, x=25, y=5 if (sb.dpytype == 1) else 10)
            print(etext.format(ecode))
            time.sleep(60)      # Show error for 1min
            sb.close()          # Revert to normal display for 30min
            time.sleep(30 * 60)
            if (not sb.reopen()):
                exit(1)
            return

        # Main execution starts here
        # Create telnet instance
        screen = roku_tn.rokuSB(display_type)

        if (not screen.open(sb_host)):
            return 1  # message already printed

        # if reset requested, do it and exit
        if (reset_sb):
            screen.close()
            print("{} reset - exiting".format(sb_host))
            return 0

        # Init counters, flags, timers, etc.
        sb_open = True
        keepalive = True
        get_weather_time = 0
        # Dispatch for each screen display
        display_panels = {0: current_conditions, 1: weather_preview, 2: local_datetime, 3: sun_rise_set}

        # Find lat/lon from location
        if ow_lat is None and ow_lon is None:
            if location is None:
                eprint("Either lat/lon or location must be specified")
                return 2

            # Determing if zip code or city,state given
            if location.isdigit():
                qloc = {'zip': location}
            else:
                qloc = {'q': location}
            qloc['appid'] = ow_appid
            resp = requests.get(ow_url_current, params=qloc)
            if (resp.status_code != 200):
                eprint("Location query returned error = {}", resp.status_code)
                eprint("Try appending 2-character country code to location.")
                return 1

            current_info = json.loads(resp.text)
            ow_lat = current_info['coord']['lat']
            ow_lon = current_info['coord']['lon']
            print("{} is located at lat: {}, lon: {}".format(location, ow_lat, ow_lon))
            # cleanup local strings
            del qloc
            del resp
            del current_info

        icon_map = wi_icons()
        # Loop until external termination request
        qforecast = {'lat': ow_lat, 'lon': ow_lon, 'units': units, 'exclude': 'hourly,minutely', 'appid': ow_appid}
        while (keepalive):
            # (Re-)open display
            if (not sb_open):
                if (screen.open(sb_host)):
                    sb_open = True
                else:
                    # Snooze a while and try again
                    time.sleep(30)
                    continue
            try:
                now = int(time.time())
                if (get_weather_time < now):
                    get_weather_time = now + 20 * 60

                    # Announce our intentions
                    screen.msg(text=getowdata, clear=True, font=1, x=25, y=5 if (display_type == 1) else 10)
                    # Get the weather from OpenWeather
                    resp = requests.get(ow_url, params=qforecast)
                    if (resp.status_code != 200):
                        openweather_error(screen, "Weather query returned error = {}", resp.status_code)
                        del resp
                        continue   # sleep & retury in loop

                    # JSON returned in text
                    wdata = json.loads(resp.text)
                    del resp

                    # Get our info from the JSON returned from OpenWeather
                    ccond = wdata['current']
                    cdescr = ccond['weather'][0]['description']
                    ccode = ccond['weather'][0]['id']
                    ctemp = int(round(ccond['temp']))

                    wspeed = int(round(ccond['wind_speed']))
                    wchill = int(round(ccond['feels_like']))
                    wdir = ccond['wind_deg']

                    humidity = ccond['humidity']
                    vis = ccond['visibility']
                    pressure = ccond['pressure']

                    wvector = wind_vector[int((float(wdir) / 22.5) + 0.5) % 16]
                    if (debug_output):
                        print("Current conditions: ({})\nTemp: {}\xb0{} {}, ".format(ccode, ctemp, temp_units, cdescr),
                              end='')
                        print("Feels like:", wchill, "Wind:", wvector, "Direction: {}deg".format(wdir))
                        print("Humidity {}%, visibility {:2.1f}mi, ".format(humidity, float(vis) / 1609.344), end='')
                        print("Pressure {:4.1f}mb".format(float(pressure)))

                    # We want am/pm in lowercase, no leading zero
                    sunrise = time.strftime("%-I:%M %P", time.localtime(ccond['sunrise']))
                    sunset = time.strftime("%-I:%M %P", time.localtime(ccond['sunset']))

                    if (debug_output):
                        print("Sunrise:", sunrise, "Sunset:", sunset)

                    # Only need today and tomorrow (1st 2)
                    today = wdata['daily'][0]
                    tomorrow = wdata['daily'][1]

                    today_high = int(round(today['temp']['max']))
                    today_low = int(round(today['temp']['min']))
                    today_time = time.localtime(today['dt'])
                    today_date = time.strftime("%e.%b", today_time)
                    today_day = time.strftime("%a", today_time)
                    today_code = today['weather'][0]['id']

                    if (debug_output):
                        print("\nForecast:")
                        print("{} {}".format(today_day, today_date), "({}) {}".format(today_code,
                                                                            today['weather'][0]['description']), end='')
                        print(", High: {}, Low: {}".format(today_high, today_low))

                    tomorrow_high = int(round(tomorrow['temp']['max']))
                    tomorrow_low = int(round(tomorrow['temp']['min']))
                    tomorrow_time = time.localtime(tomorrow['dt'])
                    tomorrow_date = time.strftime("%e.%b", tomorrow_time)
                    tomorrow_day = time.strftime("%a", tomorrow_time)
                    tomorrow_code = tomorrow['weather'][0]['id']

                    if (debug_output):
                        print("{} {}".format(tomorrow_day, tomorrow_date), "({}) {}".format(tomorrow_code,
                                                                    tomorrow['weather'][0]['description']), end='')
                        print(", High: {}, Low: {}".format(tomorrow_high, tomorrow_low))
                    # Done with response data
                    del wdata

                # Update display (select screen)
                for disp_num in range(4):
                    if (debug_output):
                        print("Screen {}: {}".format(disp_num, time.ctime()[11:19]))
                    if (display_panels[disp_num](screen)):
                        if (screen.keyproc(panel_delay) != 'TIMEOUT'):
                            keepalive = False

            except:
                exc_type, exc_value, exc_tb = sys.exc_info()
                if (sb_open):
                    screen.close()
                if (exc_type == KeyboardInterrupt):
                    return 0
                eprint("-->Caught network or other error:")
                traceback.print_exception(exc_type, exc_value, exc_tb)
                # Continue and try re-connect
                sb_open = False
                time.sleep(30)

    except Usage as err:
        if (sb_open):
            screen.close()
        eprint(err.msg)
        eprint("for help use --help")
        return 2

    finally:
        if (sb_open):
            screen.close()


if __name__ == "__main__":
    sys.exit(main())
