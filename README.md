# yarratramwatcher

This script uses the TramTracker SOAP API to check the arrival times for a given tram number and stop ID and fires an IFTTT Maker event if the upcoming arrivals are within given thresholds.

## Usage

This script is meant to be run in an minutely basis over given period of times, e.g., via Cron, as such:

	python tramwatcher.py --stop-tracker-id 3551 --route-number 86 --threshold-min-lower 4  --threshold-min-upper 6 --ifttt-event tram86to119in5min --ifttt-key bZzbMye0tNWTN9IUMxvBm4

The above call will check for the arrivals of tram 86 at stop 3551 and if there is an upcoming arrival within 4-6 minutes fires an `tram86to119in5min` IFTTT Maker event using their API key `bZzbMye0tNWTN9IUMxvBm4`.

> Note: The tram stop number is the one that appears in the TramTracker app, note the numbers used within the YarraTrams physical network.

## References

- API Docs: [http://ws.tramtracker.com.au/pidsservice/pids.asmx](http://ws.tramtracker.com.au/pidsservice/pids.asmx)
- Schema: [http://ws.tramtracker.com.au/pidsservice/pids.asmx?WSDL](http://ws.tramtracker.com.au/pidsservice/pids.asmx?WSDL)
- SOAP API Usage Example: [https://citycontrolpanel.com/api/example_scripts?l=PYTHON&fi=0](https://citycontrolpanel.com/api/example_scripts?l=PYTHON&fi=0).