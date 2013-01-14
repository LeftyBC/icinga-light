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


def poll_icinga():
    f = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "config.yaml"))
    config = yaml.load(f)

    url = config["icinga_baseurl"] + "/cgi-bin/tac.cgi?jsonoutput"
    username = config["username"] or None
    password = config["password"] or None
    interval = config["interval"] or 30

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

            services_warning = jvars["services_warning"]
            services_warning_unack = jvars["services_warning_unacknowledged"]
            services_critical = jvars["services_critical"]
            services_critical_unack = jvars["services_critical_unacknowledged"]
            services_unknown = jvars["services_unknown"]
            services_unknown_unack = jvars["services_unknown_unacknowledged"]

            hosts_down_unack = jvars["hosts_down_unacknowledged"]

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
            print "Error fetching info from %s, retrying in %d seconds." % ( url, interval )
            sleep(interval)

    # end while


if __name__ == "__main__":
    print "In AD %d, icinga polling was beginning." % \
        datetime.datetime.now().year
    try:
        poll_icinga()
    except Exception as e:
        print "Unexpected error:", sys.exc_info()[0], e
