#!/usr/bin/env python

import urllib2
import base64
import simplejson
import commands
import yaml
import os
import datetime
import sys
from time import sleep

debug = False

red = "#ff0000"
green = "#00ff00"
orange = "#ff5500"
blue = "#0000ff"
purple = "#ff00ff"
darkgreen = "#003300"
off = "off"

current_color = "#666666"

leds = {
        "service_crit": "P9.12",
        "service_warn": "P9.14",
        "service_unkn": "P9.15",
        "host_crit"   : "P9.16",
        "host_warn"   : "P9.21",
        "host_unkn"   : "P9.11"
}

def debug(msg):
    global debug
    if debug is True:
        print msg


def set_light(color="off", count=1):
    global current_color
    #if color != current_color:
    for k in range(1, count + 1, 2):
        discarded = commands.getoutput("usblamp -d 1000 \"%s\" \"%s\"" %
                                       (off, color))
    current_color = color

def tell_cylon(check_type, check_count):
	global leds
	if check_type in leds:
		if check_count is 0:
			digitalWrite(leds[check_type], LOW)
		else:
			for i in range(1,check_count):
				digitalWrite(leds[check_type], LOW)
				delay(100)
				digitalWrite(leds[check_type], HIGH)

def poll_icinga():

    if cylon_mode:
	from mrbbio import *
	for led in leds:
		pinUnexport(digitalPinDef[leds[led]])
		pinMode(leds[led], OUTPUT)

    # build request, auth'd if necessary
    request = urllib2.Request(url)
    if (username and password):
        # add authorization data if username/password has been specified
        base64string = base64.encodestring('%s:%s' % (username, password))
        base64string = base64string.replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)

    while True:
        try:
            debug("Loading " + url)
            result = urllib2.urlopen(request)
            json = simplejson.load(result)

            jvars = json["tac"]["tac_overview"]

            host_pct = jvars["percent_host_health"]
            service_pct = jvars["percent_service_health"]

            services_warning = int(jvars["services_warning"])
            services_warning_unack = int(jvars["services_warning_unacknowledged"])
            services_critical = int(jvars["services_critical"])
            services_critical_unack = jvars["services_critical_unacknowledged"]
            services_unknown = int(jvars["services_unknown"])
            services_unknown_unack = int(jvars["services_unknown_unacknowledged"])

            hosts_down_unack = int(jvars["hosts_down_unacknowledged"])
            hosts_warn_unack = int(jvars["hosts_unreachable_unacknowledged"])
            hosts_unknown_unack = int(jvars["hosts_pending"])
		
	    if cylon_mode:
	            tell_cylon("service_crit", services_critical_unack)
		    tell_cylon("service_warn", services_warning_unack)
		    tell_cylon("service_unkn", services_unknown_unack)

		    tell_cylon("host_crit", hosts_down_unack)
		    tell_cylon("host_warn", hosts_warn_unack)
		    tell_cylon("host_unkn", hosts_unknown_unack)
		
	    else:
		    # assume we're using the notifier instead

		    if services_critical_unack > 0:
			debug("crit srv: " + str(services_critical_unack))
			set_light(color=red, count=services_critical_unack)
		    elif services_warning_unack > 0:
			debug("warn srv: " + str(services_warning_unack))
			set_light(color=orange, count=services_warning_unack)
		    elif hosts_down_unack > 0:
			debug("hosts down: " + str(hosts_down_unack))
			set_light(color=blue, count=hosts_down_unack)
		    elif services_unknown_unack > 0:
			debug("services unknown: " + str(services_unknown_unack))
			set_light(color=purple, count=services_unknown_unack)
		    else:
			debug("all is well")
			if current_color != darkgreen:
			    set_light(color=darkgreen)

            sleep(interval)
        except urllib2.URLError:
            print "Error fetching info from %s, retrying in %d seconds." % ( url, int(interval) )
            sleep(interval)

	except KeyboardInterrupt:
	    print "Cleaning up"
	    if cylon_mode:
		    cleanup()

    # end while


if __name__ == "__main__":
    f = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "config.yaml"))
    config = yaml.load(f)

    url = config["icinga_baseurl"] + "/cgi-bin/tac.cgi?jsonoutput"
    username = config["username"] or None
    password = config["password"] or None
    interval = int(config["interval"]) or 30
    cylon_mode = config["enable_cylon"] or False

    print "In AD %d, icinga polling was beginning." % \
        int(datetime.datetime.now().year)
    try:
        poll_icinga()
    except KeyboardInterrupt:
	print "Exiting gracefully, I hope"
	if cylon_mode:
		cleanup()
    except Exception as e:
        print "Unexpected error:", sys.exc_info()[0]
	raise
