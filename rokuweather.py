#!/usr/bin/env python3

"""rokuweather [opts] RokuSB

Hostname or IP of RokuSB required argument

Command-line opts:

-h, --help      This text
-v, --verbose   Turn on debug output
-l, --location  Location (City,State) Default: "Boston,MA"
-t, --type      Display type (1 := M1000/1, 2 := R1000)
-r, --reset     Reset Soundbridge and exit sketch

"""
import sys
import getopt
import time

import requests
import xml.etree.ElementTree as ET
from urllib import parse

from draw_icon import draw_icon
import roku_tn


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def main(argv=None):
    # Some constant defs
    getyahoodata = "Getting weather data from Yahoo..."
    yql_url = "https://query.yahooapis.com/v1/public/yql?q="
    ns = {'yweather': 'http://xml.weather.yahoo.com/ns/rss/1.0'}

    temp_units = 'F'
    speed_units = 'mph'

    wind_vector = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']

    location = "Boston,MA"
    # Type 1 := 280x16, 2 := 280x32
    display_type = 1
    sb_open = False

    # Single panel display time
    dpy_delay = 10

    # Parse any command-line args
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hvl:t:r", ["help", "verbose", "location=", "type="])
        except getopt.error as msg:
            raise Usage(msg)

        # Gather command options
        debug_output = False
        reset_sb = False
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

        # Remaining arg is display host
        if (len(args) != 1):
            raise Usage("Display host name or IP required")

        sb_host = args[0]

        # Local sisplay panel functions
        def current_conditions(sb, dpy_type):
            # Roku current weather to display
            fnt = 1 if (dpy_type == 1) else 2
            xoff = 80 if (dpy_type == 1) else 90
            sb.msg(text=ctemp + "\xb0" + temp_units, font=10 if (dpy_type == 1) else 3, x=34, y=0, clear=True)
            sb.msg(text="{}, Humidity: {}%".format(ccond, humidity), font=fnt, x=xoff, y=0)
            sb.msg(text="Wind: {} at {}{}, Chill: {}\xb0{}".format(wvector, wspeed, speed_units, wchill, temp_units),
                                                                font=fnt, x=xoff, y=8 if (dpy_type == 1) else 16)
            draw_icon(sb, ccode, 0, 0)
            return True

        def weather_preview(sb, dpy_type):
            # Roku weather preview to display
            #  rest of today
            ds = today_date.split()     # Need to fixup day to 2 digits
            if (len(ds[0]) == 1):
                ds[0] = ' ' + ds[0]
            fnt = 1 if (dpy_type == 1) else 2
            ymax = 15 if (dpy_type == 1) else 31
            yoff = 8 if (dpy_type == 1) else 16
            sb.msg(text=today_day, font=fnt, x=0, y=0, clear=True)  # day
            sb.msg(text="{}.{}".format(ds[0], ds[1]), x=0, y=yoff)  # date
            sb.msg(text=today_high + "\xb0" + temp_units, x=82, y=0)  # max temp
            sb.msg(text=today_low + "\xb0" + temp_units, x=82, y=yoff)  # min temp
            # Clear second half and  draw border line
            sb.cmd("sketch -c color 0")
            sb.cmd("sketch -c rect 139 0 141 {}".format(ymax))
            sb.cmd("sketch -c color 1")
            sb.cmd("sketch -c line 140 0 140 {}".format(ymax))
            # tomorrow
            ds = tomorrow_date.split()
            if (len(ds[0]) == 1):
                ds[0] = ' ' + ds[0]
            xoff = 227 if (dpy_type == 1) else 233
            sb.msg(text=tomorrow_day, font=fnt, x=145, y=0)  # day
            sb.msg(text="{}.{}".format(ds[0], ds[1]), x=145, y=yoff)  # date
            sb.msg(text=tomorrow_high + "\xb0" + temp_units, x=xoff, y=0)  # max temp
            sb.msg(text=tomorrow_low + "\xb0" + temp_units, x=xoff, y=yoff)  # min temp

            draw_icon(sb, today_code, 47 if (dpy_type == 1) else 49, 0)
            draw_icon(sb, tomorrow_code, 188 if (dpy_type == 1) else 194, 0)
            return True

        def local_datetime(sb, dpy_type):
            datetime = time.ctime()
            sb.msg(text=datetime[11:16] + "   " + datetime[:3] + ", " + datetime[4:10],
                                                clear=True, font=10 if (dpy_type == 1) else 2, x=80, y=0)
            return True if (dpy_type == 1) else False

        def sun_rise_set(sb: object, dpy_type: object) -> object:
            fnt = 10 if (dpy_type == 1) else 2
            yoff = 0 if (dpy_type == 1) else 16
            sb.msg(text="Sunrise: " + sunrise, font=fnt, x=8, y=yoff, clear=True if (dpy_type == 1) else False)
            sb.msg(text="Sunset: " + sunset, font=fnt, x=148, y=yoff)
            return True

        # Main execution starts here
        # Create telnet instance
        screen = roku_tn.rokuSB(display_type)

        # if reset requested, do it and exit
        if (reset_sb):
            if (screen.open(sb_host)):
                screen.close()
                print("{} reset - exiting".format(sb_host))
                return 0
            else:
                return 1    # message already printed

        # Init counters, flags, timers, etc.
        keepalive = True
        get_weather_time = 0
        # Dispatch for each screen display
        display_panels = {0: current_conditions, 1: weather_preview, 2: local_datetime, 3: sun_rise_set}

        # Query yahoo for location id (woeid)
        loc_query = 'select woeid from geo.places where text="' + location + '"'
        qres = requests.get(yql_url + parse.quote(loc_query))
        if (qres.status_code != 200):
            print("Location query returned error = ", qres.status_code)
            return 1

        root = ET.fromstring(qres.content)
        del qres

        place = root.find('.//{http://where.yahooapis.com/v1/schema.rng}place')
        woeid = place[0].text

        if (woeid is None):
            print("Location query for {} failed".format(location))
            return 1

        if (debug_output):
            print("Location:", location, "(woeid = " + woeid + ")")

        # Loop until external termination request
        while (keepalive):

            if (not sb_open):
                if (screen.open(sb_host)):
                    sb_open = True
                    screen.msg(encoding='utf8')
                else:
                    # Snooze a while and try again
                    time.sleep(30)
                    continue
            try:
                now = int(time.time())
                if (get_weather_time < now):
                    get_weather_time = now + 20 * 60

                    # Announce our intentions
                    screen.clear()
                    if (display_type == 2):
                        screen.msg(text=getyahoodata, font=1, x=25, y=10)
                    else:
                        screen.msg(text=getyahoodata, font=1, x=25, y=5)

                    # Get the weather using woeid from yahoo
                    w_query = 'select * from weather.forecast where woeid="' + woeid + '"'
                    qres = requests.get(yql_url + parse.quote(w_query))
                    if (qres.status_code != 200):
                        print("Weather query returned error = ", qres.status_code)
                        break   # sleep & retury in loop

                    root = ET.fromstring(qres.content)
                    del qres

                    # Parse the returned XML from Yahoo
                    cond = root.find('.//yweather:condition', ns)
                    ccond = cond.attrib.get('text')
                    ctemp = cond.attrib.get('temp')
                    ccode = cond.attrib.get('code')

                    wind = root.find('.//yweather:wind', ns)
                    wspeed = wind.attrib.get('speed')
                    wchill = wind.attrib.get('chill')
                    wdir = wind.attrib.get('direction')

                    atmos = root.find('.//yweather:atmosphere', ns)
                    humidity = atmos.attrib.get('humidity')
                    vis = atmos.attrib.get('visibility')
                    pressure = atmos.attrib.get('pressure')
                    rising = atmos.attrib.get('rising')
                    baro = {'0': 'steady', '1': 'rising', '2': 'falling'}[rising]

                    wvector = wind_vector[int(float(wdir) / 22.5)]
                    if (debug_output):
                        print("Current conditions: ({})\nTemp: {}\xb0{} {}, ".format(ccode, ctemp, temp_units, ccond),
                              end='')
                        print("Feels like:", wchill, "Wind:", wvector, "Direction: {}deg".format(wdir))
                        print("Humidity {}%, visibility {:2.1f}mi, ".format(humidity, float(vis)), end='')
                        print("Pressure {:4.1f}mb, {}".format(float(pressure), baro))

                    astro = root.find('.//yweather:astronomy', ns)
                    sunrise = astro.attrib.get('sunrise')
                    if (sunrise[4] != ' '):
                        sunrise = sunrise[:2] + '0' + sunrise[2:]
                    sunset = astro.attrib.get('sunset')
                    if (sunset[4] != ' '):
                        sunset = sunset[:2] + '0' + sunset[2:]

                    if (debug_output):
                        print("Sunrise", sunrise, "Sunset", sunset)

                    # Only need today and tomorrow (1st 2)
                    today = None
                    tomorrow = None
                    for yw in root.findall('.//yweather:forecast', ns):
                        if (today is None):
                            today = yw
                            continue

                        if (tomorrow is None):
                            tomorrow = yw
                            break

                    today_high = today.attrib.get('high')
                    today_low = today.attrib.get('low')
                    today_date = today.attrib.get('date')
                    today_day = today.attrib.get('day')
                    today_code = today.attrib.get('code')

                    if (debug_output):
                        print("\nForecast:")
                        print("{} {}".format(today_day, today_date), "({}) {}".format(today_code,
                                                                            today.attrib.get('text')), end='')
                        print(", High: {}, Low: {}".format(today_high, today_low))

                    tomorrow_high = tomorrow.attrib.get('high')
                    tomorrow_low = tomorrow.attrib.get('low')
                    tomorrow_date = tomorrow.attrib.get('date')
                    tomorrow_day = tomorrow.attrib.get('day')
                    tomorrow_code = tomorrow.attrib.get('code')

                    if (debug_output):
                        print("{} {}".format(tomorrow_day, tomorrow_date), "({}) {}".format(tomorrow_code,
                                                                    tomorrow.attrib.get('text')), end='')
                        print(", High: {}, Low: {}".format(tomorrow_high, tomorrow_low))

                # Update display (select screen)
                for disp_num in range(4):
                    if (display_panels[disp_num](screen, screen.dpytype)):
                        time.sleep(dpy_delay)

            except:
                err = sys.exc_info()[0]
                if (sb_open):
                    screen.close()
                    sb_open = False
                if (err == KeyboardInterrupt):
                    return 0
                eprint("Network or other error:", err)
                # Continue and try re-connect
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
