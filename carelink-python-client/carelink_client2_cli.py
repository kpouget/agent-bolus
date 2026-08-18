###############################################################################
#  
#  Carelink Client 2 CLI
#  
#  Description:
#
#    This is the command line interface of the Carelink Client. It is used
#    to download a patients recent pump and sensor data from the Carelink 
#    Cloud. The data is saved to a JSON file.
#  
#  Author:
#
#    Ondrej Wisniewski (ondrej.wisniewski *at* gmail.com)
#  
#  Changelog:
#
#    31/12/2023 - Initial version
#
#  Copyright 2023, Ondrej Wisniewski 
#
###############################################################################

import carelink_client2
import argparse
import time
import json
import datetime
import os

VERSION = "1.0"


def writeJson(jsonobj, name):
   # Create data directory in parent directory (main project data folder)
   data_dir = os.path.join("..", "data")
   os.makedirs(data_dir, exist_ok=True)

   filename = os.path.join(data_dir, name + "-" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")
   try:
      f = open(filename, "w")
      f.write(json.dumps(jsonobj,indent=3))
      f.close()
   except Exception as e:
      print("ERROR: failed to save %s (%s) " % (filename, str(e)))
      return False
   else:
      print("JSON data saved to %s" % filename)
      return True


# Parse command line
parser = argparse.ArgumentParser()
parser.add_argument('--repeat',    '-r', type=int, help='Repeat request times', required=False)
parser.add_argument('--wait',      '-w', type=int, help='Wait minutes between repeated calls', required=False)
parser.add_argument('--data',      '-d', help='Save recent data', action='store_true')
parser.add_argument('--history',   '-H', type=int, help='Download historical data for N days back (default: 7)', const=7, nargs='?')
parser.add_argument('--web',       '-W', help='Use web interface API (may have more historical data)', action='store_true')
parser.add_argument('--csv',       '-C', type=int, help='Generate and download CSV report for N days (default: 14)', const=14, nargs='?')
parser.add_argument('--verbose',   '-v', help='Verbose mode', action='store_true')
args = parser.parse_args()

# Get parameters from CLI
repeat   = 1 if args.repeat == None else args.repeat
wait     = 5 if args.wait == None else args.wait
data     = args.data
history  = args.history
web      = args.web
csv      = args.csv
verbose  = args.verbose

#print("repeat   = " + str(repeat))
#print("wait     = " + str(wait))
#print("data     = " + str(data))
#print("history  = " + str(history))
#print("web      = " + str(web))
#print("csv      = " + str(csv))
#print("verbose  = " + str(verbose))

# Create client instance
client = carelink_client2.CareLinkClient()
if verbose:
   print("Client created")
   
if client.init():
   client.printUserInfo()
   for i in range(repeat):
      if verbose:
         print("Starting download, count: %d" % (i+1))
      try:
         # Handle CSV generation and download
         if csv is not None:
            days = csv if csv > 0 else 14
            if verbose:
               print(f"Generating and downloading CSV report for {days} days")
            csv_data = client.generateAndDownloadCsvReport(days_back=days)
            filename_prefix = f"csv_report_{days}days"

            # Save CSV data to .csv file
            if csv_data and isinstance(csv_data, str):
               # Create data directory in parent directory (main project data folder)
               data_dir = os.path.join("..", "data")
               os.makedirs(data_dir, exist_ok=True)

               csv_filename = os.path.join(data_dir, filename_prefix + "-" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv")
               try:
                  with open(csv_filename, "w") as f:
                     f.write(csv_data)
                  print(f"CSV data saved to {csv_filename}")
                  if verbose:
                     print(f"File size: {len(csv_data)} characters")
                  continue  # Skip the JSON saving part
               except Exception as e:
                  print("ERROR: failed to save CSV file %s (%s)" % (csv_filename, str(e)))
                  break
            else:
               print("ERROR: No CSV data received or invalid format")
               break
         # Handle other data sources
         elif web:
            if verbose:
               print("Downloading data from web interface API")
            downloadedData = client.getWebData()
            filename_prefix = "webdata"
         elif history is not None:
            if verbose:
               print("Downloading historical data for %d days" % history)
            downloadedData = client.getHistoricalData(days_back=history)
            filename_prefix = "history_%ddays" % history
         else:
            if verbose:
               print("Downloading recent data")
            downloadedData = client.getRecentData()
            filename_prefix = "data"

         if downloadedData != None and client.getLastResponseCode() == 200:
            if data or history is not None or web:  # Auto-save for JSON data types
               if writeJson(downloadedData, filename_prefix):
                  if verbose:
                     if web:
                        print("Web interface data downloaded (may contain more history)")
                     elif history is not None:
                        print("Historical data requested for %d days" % history)
         # Error occurred
         else:
            print("ERROR: failed to get data (response code %d)" % client.getLastResponseCode())
            break
      except Exception as e:
         print(e)
         break
            
      if i < repeat - 1:
         if verbose:
            print("Waiting %d minutes before next download" % wait)
         time.sleep(wait * 60)
else:
   print("ERROR: failed to initialize client (response code %s)" % client.getLastResponseCode())
