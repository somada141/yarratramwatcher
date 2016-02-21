"""

References:

- API Docs: http://ws.tramtracker.com.au/pidsservice/pids.asmx
- Schema: http://ws.tramtracker.com.au/pidsservice/pids.asmx?WSDL
- Usage Example: https://citycontrolpanel.com/api/example_scripts?l=PYTHON&fi=0
"""


import logging
import datetime
import argparse

import dateutil.parser
import pytz
import requests
import suds
from suds.xsd.doctor import ImportDoctor, Import


# create a logger
logging.basicConfig()
logger = logging.getLogger("tramwatcher")
logger.setLevel(logging.DEBUG)


def create_client():
    """"""

    url = "http://ws.tramtracker.com.au/pidsservice/pids.asmx?WSDL"

    # dodgy to fix the `TypeNotFound` error. Solution based on information from
    # https://bitbucket.org/jurko/suds/issues/20/typenotfound-schema
    imp = Import('http://www.w3.org/2001/XMLSchema', 
        location='http://www.w3.org/2001/XMLSchema.xsd')
    imp.filter.add("http://microsoft.com/wsdl/types/")
    doctor = ImportDoctor(imp)

    msg_fmt = u"Creating SOAP API client to URL '{0}'".format(url)
    logger.info(msg_fmt)

    # create a new SOAP client
    client = suds.client.Client(url, doctor=doctor)

    msg_fmt = u"Retrieving TramTracker API client GUID to URL"
    logger.debug(msg_fmt)

    # retrieve a new GUID to authorize the API calls
    guid = client.service.GetNewClientGuid()

    msg_fmt = u"TramTracker API client GUID '{0}' retrieved".format(guid)
    logger.debug(msg_fmt)

    # create a new `PidsClientHeader`
    header = client.factory.create("PidsClientHeader")

    # set the necessary header parameters
    header.ClientGuid = guid
    # header.ClientType = "type"
    header.ClientVersion = "1.0"
    header.ClientWebServiceVersion = "6.4.0.0"
    header.OSVersion = "1.0"

    msg_fmt = u"TramTracker API SOAP headers set to '{0}'".format(header)
    logger.debug(msg_fmt)

    client.set_options(soapheaders=[header])

    return client


def get_next_arrivals(client, stop_tracker_id, route_number, convert_utc=True):
    """"""

    msg = u"Retrieving predicted arrival times for stop '{0}' and route '{1}'"
    msg_fmt = msg.format(stop_tracker_id, route_number)
    logger.info(msg_fmt)

    # perform `GetNextPredictedRoutesCollection` request for the given stop and tram
    # number
    response = client.service.GetNextPredictedRoutesCollection(stopNo=stop_tracker_id, 
                                                               routeNo=route_number, 
                                                               lowFloor=False)

    # get the prediction result list
    result = response.GetNextPredictedRoutesCollectionResult
    predictions = result.diffgram[0].DocumentElement[0].ToReturn

    # loop over the predicted arrivals, parse the datetimes, and (optionally) convert
    # the datetimes to UTC
    arrivals = []
    for prediction in predictions:
        tzutc = pytz.timezone("UTC")
        dt = dateutil.parser.parse(prediction.PredictedArrivalDateTime[0]) 

        if convert_utc:
            dt = dt.astimezone(tzutc)

        arrivals.append(dt)

    return arrivals


def get_seconds_till_arrivals(client, stop_tracker_id, route_number):
    """"""

    msg = u"Calculating time until arrival for stop '{0}' and route '{1}'"
    msg_fmt = msg.format(stop_tracker_id, route_number)
    logger.info(msg_fmt)

    # get the UTC arrival datetimes for the given tram stop and number
    arrivals = get_next_arrivals(client=client, 
                                 stop_tracker_id=stop_tracker_id, 
                                 route_number=route_number,
                                 convert_utc=True)

    # calculate the number of seconds between now and the different
    # arrival times
    seconds_arrivals = []
    for arrival in arrivals:
        tzutc = pytz.timezone("UTC")
        dt_now = datetime.datetime.utcnow()
        dt_now = tzutc.localize(dt_now)

        delta = arrival - dt_now
        seconds_arrivals.append(delta.total_seconds())

    return seconds_arrivals


def notify_ifttt(event, key):
    """Notifies IFTTT's Maker that an `event` has occured"""

    msg = u"Posting IFTTT notification with event name '{0}'"
    msg_fmt = msg.format(event)
    logger.info(msg_fmt)

    # set the IFTTT Maker URL
    url_ifttt = "https://maker.ifttt.com/trigger/{event}/with/key/{key}"
    url_ifttt = url_ifttt.format(event=event, key=key)

    # perform a GET request
    response = requests.get(url_ifttt)

    return response


def main(arguments):
    """"""
    client = create_client()

    seconds_arrivals = get_seconds_till_arrivals(client=client,
                                                 stop_tracker_id=arguments.stop_tracker_id,
                                                 route_number=arguments.route_number)

    msg = u"Seconds till next arrivals for stop '{0}' and route '{1}': '{2}'"
    msg_fmt = msg.format(arguments.stop_tracker_id, 
                         arguments.route_number, 
                         seconds_arrivals)
    logger.info(msg_fmt)    

    for seconds in seconds_arrivals:
        if ((seconds >= arguments.threshold_min_lower * 60) and 
            (seconds <= arguments.threshold_min_upper * 60)):

            msg = u"Tram '{0}' arriving at stop '{1}' within '{2}' and '{3}' minutes"
            msg_fmt = msg.format(arguments.route_number,
                                 arguments.stop_tracker_id,
                                 arguments.threshold_min_lower,
                                 arguments.threshold_min_upper)
            print notify_ifttt(event=arguments.ifttt_event, key=arguments.ifttt_key)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Yarra Trams watcher and IFTTT notifier')
    parser.add_argument("--stop-tracker-id",
                        dest="stop_tracker_id", 
                        type=int,
                        default=3551,
                        help="Stop number as it appears in TramTracker",
                        required=False)
    parser.add_argument("--route-number",
                        dest="route_number", 
                        type=int,
                        default=86,
                        help="Tram/route number as defined in the YarraTrams network",
                        required=False)
    parser.add_argument("--threshold-min-lower",
                        dest="threshold_min_lower", 
                        type=int,
                        default=4,
                        help="Lower minute threshold for event triggering",
                        required=False)
    parser.add_argument("--threshold-min-upper",
                        dest="threshold_min_upper", 
                        type=int,
                        default=6,
                        help="Upper minute threshold for event triggering",
                        required=False)
    parser.add_argument("--ifttt-event",
                        dest="ifttt_event", 
                        type=str,
                        default="tram86to119in5min",
                        help="IFTTT Maker event to be triggered",
                        required=False)
    parser.add_argument("--ifttt-key",
                        dest="ifttt_key", 
                        type=str,
                        default="bZzbMye0tNWTN9IUMxvBm4",
                        help="IFTTT Maker event to be triggered",
                        required=False)
    arguments_cli = parser.parse_args()
    main(arguments=arguments_cli)
