###############################################################################
#  
#  Carelink Client 2 library
#  
#  Description:
#
#    This library implements a client for the Medtronic Carelink API
#    as used by the official Carelink Connect Android app.
#  
#  Author:
#
#    Ondrej Wisniewski (ondrej.wisniewski *at* gmail.com)
#  
#  Changelog:
#
#    28/12/2023 - Initial version
#    11/04/2024 - Check for valid data in API response in _get_data()
#    19/11/2024 - Update CARELINK_CONFIG_URL
#    11/02/2025 - Update CARELINK_CONFIG_URL to ver 3.3
#    03/01/2026 - Fix for new Auth method (by @m0rt4l1n)
#
#  Copyright 2023-2026, Ondrej Wisniewski
#
###############################################################################

# Workflow
# --------
#
# [0.1] GET access_token, refresh_token, mag-identifier from login procedure
# carelink_carepartner_api_login.py
#
# [0.2] GET base_urls (region=US or region=EU) and sso_config urls
# GET https://clcloud.minimed.eu/connect/carepartner/v11/discover/android/3.3
#
# [1] GET role from "baseUrlCareLink"
# GET /api/carepartner/v2/users/me
#
# [2] GET patientId from "baseUrlCareLink"
# GET /api/carepartner/v2/links/patients
#
# [3] GET data (providing username, role, patientId) from "baseUrlCumulus"
# POST /connect/carepartner/v11/display/message
#
# [4] REFRESH access_token, refresh_token from 
# sso_config["server"]["hostname"]:sso_config["server"]["port"]/sso_config["server"]["prefix"]/sso_config["system_endpoints"]["token_endpoint_path"]
# POST /auth/oauth/v2/token

import json
import requests
import time
import base64
import os
import logging as log
from datetime import datetime, timedelta

 
# Version string
VERSION = "1.4"

# Constants
DEFAULT_FILENAME="logindata.json"
CARELINK_CONFIG_URL = "https://clcloud.minimed.eu/connect/carepartner/v13/discover/android/3.6"
AUTH_ERROR_CODES = [401,403]
COMMON_HEADERS = {
                  "Accept": "application/json",
                  "Content-Type": "application/json",
                  "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; Nexus 5X Build/QQ3A.200805.001)",
                 }

# Logging config
FORMAT = "[%(asctime)s:%(levelname)s] %(message)s"
log.basicConfig(format=FORMAT, datefmt="%Y-%m-%d %H:%M:%S", level=log.INFO)


###########################################################
# Class CareLinkClient
###########################################################
class CareLinkClient(object):
   
   def __init__(self, tokenFile=DEFAULT_FILENAME):
      
      self.__version = VERSION
      
      # Authorization
      self.__tokenFile = tokenFile
      self.__tokenData = None
      self.__accessTokenPayload = None
      
      # API config
      self.__config = None
      
      # User info
      self.__username = None
      self.__user = None
      self.__patient = None 
      self.__country = None
      
      # API status
      self.__last_api_status = None
      
   ###########################################################
   # Class internal functions
   ###########################################################
   
   ###########################################################
   # Read token file
   ###########################################################
   def _read_token_file(self, filename):
      log.info("_read_token_file()")
      token_data = None
      if os.path.isfile(filename):
         try:
            token_data = json.loads(open(filename, "r").read())
         except json.JSONDecodeError:
            log.error("ERROR: failed parsing token file %s" % filename)

         if token_data is not None:
            required_fields = ["access_token", "refresh_token", "scope", "client_id"]
            for f in required_fields:
               if f not in token_data:
                  log.error("ERROR: field %s is missing from token file" % f)
      else:
         log.error("ERROR: token file %s not found" % filename)
      return token_data

   ###########################################################
   # Write token file
   ###########################################################
   def _write_token_file(self, obj, filename):
      log.info("_write_token_file()")
      with open(filename, 'w') as f:
         json.dump(obj, f, indent=4)

   ###########################################################
   # Get Carelink API config
   ###########################################################
   def _get_config(self, discovery_url, country):
      log.info("_get_config()")
      resp = requests.get(discovery_url)
      log.debug("   status: %d" % resp.status_code)
      data = resp.json()
      region = None
      config = None

      for c in data["supportedCountries"]:
         try:
            region = c[country.upper()]["region"]
            break
         except KeyError:
            pass
      if region is None:
         raise Exception("ERROR: country code %s is not supported" % country)
      log.debug("   region: %s" % region)
      
      for c in data["CP"]:
         if c["region"] == region:
            config = c
            break
      if config is None:
         raise Exception("ERROR: failed to get config base urls for region %s" % region)

      sso_configuration_key = config["UseSSOConfiguration"]
      resp = requests.get(config[sso_configuration_key])
      log.debug("   status: %d" % resp.status_code)
      sso_config = resp.json()
      sso_base_url = "https://%s:%d/%s" % (sso_config["server"]["hostname"],
                                           sso_config["server"]["port"],
                                           sso_config["server"]["prefix"])
      if sso_base_url.endswith('/'):
         sso_base_url = sso_base_url[:-1] # remove trailing slash if prefix is empty

      token_url = sso_base_url + sso_config["system_endpoints"]["token_endpoint_path"]
      c["token_url"] = token_url
      return config
   
   ###########################################################
   # Get user data
   ###########################################################
   def _get_user(self, config, token_data):
      log.info("_get_user()")
      url = config["baseUrlCareLink"] + "/users/me"
      headers = COMMON_HEADERS
      if "mag-identifier" in token_data:
         headers["mag-identifier"] = token_data["mag-identifier"]
      headers["Authorization"] = "Bearer " + token_data["access_token"]
      self.__last_api_status = None
      resp = requests.get(url=url,headers=headers)
      self.__last_api_status = resp.status_code
      log.debug("   status: %d" % resp.status_code)
      try:
         user = resp.json()
      except:
         user = None
      return user

   ###########################################################
   # Get patient data
   ###########################################################
   def _get_patient(self, config, token_data):
      log.info("_get_patient()")
      url = config["baseUrlCareLink"] + "/links/patients"
      headers = COMMON_HEADERS
      if "mag-identifier" in token_data:
         headers["mag-identifier"] = token_data["mag-identifier"]
      headers["Authorization"] = "Bearer " + token_data["access_token"]
      self.__last_api_status = None
      resp = requests.get(url=url,headers=headers)
      self.__last_api_status = resp.status_code
      log.debug("   status: %d" % resp.status_code)
      try:
         patient = resp.json()[0]
      except:
         patient = None
      return patient

   ###########################################################
   # Get periodic pump and sensor data
   ###########################################################
   def _get_data(self, config, token_data, username, role, patientid, start_date=None, end_date=None):
      log.info("_get_data()")
      url = config["baseUrlCumulus"] + "/display/message"
      headers = COMMON_HEADERS
      if "mag-identifier" in token_data:
         headers["mag-identifier"] = token_data["mag-identifier"]
      headers["Authorization"] = "Bearer " + token_data["access_token"]
      data = {}
      data["username"] = username
      if role in ["CARE_PARTNER","CARE_PARTNER_OUS"]:
         data["role"] = "carepartner"
         data["patientId"] = patientid
      else:
         data["role"] = "patient"

      # Add date range parameters if provided - try multiple formats
      if start_date and end_date:
         # Try different parameter names and date formats
         data["startDate"] = start_date
         data["endDate"] = end_date
         data["from"] = start_date
         data["to"] = end_date
         data["beginDate"] = start_date
         data["fromDate"] = start_date
         data["toDate"] = end_date

         # Also try ISO format with time
         iso_start = start_date + "T00:00:00.000Z"
         iso_end = end_date + "T23:59:59.999Z"
         data["startDateTime"] = iso_start
         data["endDateTime"] = iso_end

         log.info("   requesting data from %s to %s" % (start_date, end_date))
         log.info("   trying multiple date parameter formats")
      else:
         log.info("   requesting recent data (no date range)")

      log.info("   POST data: %s" % json.dumps(data))
      #log.debug("url: %s" % url)
      #log.debug("headers: %s" % json.dumps(headers))

      self.__last_api_status = None
      resp = requests.post(url=url,headers=headers,data=json.dumps(data))
      self.__last_api_status = resp.status_code
      log.info("   API response status: %d" % resp.status_code)

      try:
         my_data = resp.json()

         # Analyze response to see date range
         if my_data and isinstance(my_data, dict):
            # Look for data arrays that might contain timestamped entries
            for key in ['sgs', 'markers', 'readings', 'events', 'data']:
               if key in my_data and isinstance(my_data[key], list) and len(my_data[key]) > 0:
                  log.info("   Found %d entries in '%s'" % (len(my_data[key]), key))

                  # Try to find date range in the data
                  dates = []
                  for entry in my_data[key][:5]:  # Check first 5 entries
                     if isinstance(entry, dict):
                        for date_field in ['datetime', 'timestamp', 'date', 'time', 'sg_datetime']:
                           if date_field in entry:
                              dates.append(entry[date_field])
                              break

                  if dates:
                     log.info("   Data dates sample: %s" % dates[:3])

            # Check if response includes any date-related metadata
            if 'lastSensorTSAsString' in my_data:
               log.info("   Last sensor timestamp: %s" % my_data['lastSensorTSAsString'])

      except Exception as e:
         log.warning("   Could not parse response JSON: %s" % str(e))
         my_data = None

      return my_data

   ###########################################################
   # Do token data refresh
   ###########################################################
   def _do_refresh(self, config, token_data):
      log.info("_do_refresh()")
      token_url = config["token_url"]
      data = {
         "refresh_token": token_data["refresh_token"],
         "client_id":     token_data["client_id"],
         "grant_type":    "refresh_token"
         }
      if "client_secret" in token_data:
         data["client_secret"] = token_data["client_secret"]
      headers = {}
      if "mag-identifier" in token_data:
         headers["mag-identifier"] = token_data["mag-identifier"]
      resp = requests.post(url=token_url, headers=headers, data=data)
      log.debug("   status: %d" % resp.status_code)
      if resp.status_code != 200:
         raise Exception("ERROR: failed to refresh token")
      new_data = resp.json()
      token_data["access_token"] = new_data["access_token"]
      token_data["refresh_token"] = new_data["refresh_token"]
      return token_data

   ###########################################################
   # Get access token payload 
   ###########################################################
   def _get_access_token_payload(self, token_data):
      log.info("_get_access_token_payload()")
      try:
         token = token_data["access_token"]
      except:
         log.debug("   no access token found")
         return None
      try:
         # Decode json web token payload
         payload_b64 = token.split('.')[1]
         payload_b64_bytes = payload_b64.encode()
         missing_padding = (4 - len(payload_b64_bytes) % 4) % 4
         if missing_padding:
            payload_b64_bytes += b'=' * missing_padding
         payload_bytes = base64.b64decode(payload_b64_bytes)
         payload = payload_bytes.decode()
         payload_json = json.loads(payload)
         #log.debug(payload_json)
      except:
         log.info("   malformed access token")
         return None
      return payload_json

   ###########################################################
   # Check access token validity
   ###########################################################
   def _is_token_valid(self, access_token_payload):
      log.info("_is_token_valid()")
      try:
         # Get expiration time stamp
         token_validto = access_token_payload["exp"]
      except:
         log.info("   missing data in access token")
         return False
      
      # Check expiration time stamp
      tdiff = token_validto - time.time()
      if tdiff < 0:
         log.info("   access token has expired %ds ago" % abs(tdiff))
         return False
      if tdiff < 600:
         log.info("   access token is about to expire in %ds" % abs(tdiff))
         return False
      
      # Token is valid
      auth_token_validto = datetime.utcfromtimestamp(token_validto).strftime("%a %b %d %H:%M:%S UTC %Y")
      log.info("   access token expires in %ds (%s)" % (tdiff,auth_token_validto))
      return True

   ###########################################################
   # Init static data
   ###########################################################
   def _init(self):
      self.__tokenData = self._read_token_file(self.__tokenFile)
      if self.__tokenData is None:
         return False
      self.__accessTokenPayload = self._get_access_token_payload(self.__tokenData)
      if self.__accessTokenPayload is None:
         return False
      try:
         self.__country = self.__accessTokenPayload["token_details"]["country"]
         self.__config = self._get_config(CARELINK_CONFIG_URL, self.__country)
         self.__username = self.__accessTokenPayload["token_details"]["preferred_username"]
         self.__user = self._get_user(self.__config, self.__tokenData)
         if self.__user["role"] in ["CARE_PARTNER","CARE_PARTNER_OUS"]:
            self.__patient = self._get_patient(self.__config, self.__tokenData)
      except Exception as e:
         log.error(e)
         if self.__last_api_status in AUTH_ERROR_CODES:
            try:
               self.__tokenData = self._do_refresh(self.__config, self.__tokenData)
               self.__accessTokenPayload = self._get_access_token_payload(self.__tokenData)
               self._write_token_file(self.__tokenData, self.__tokenFile)
            except Exception as e:
               log.error(e)
         return False
      return True


   ###########################################################
   # Class public functions
   ###########################################################

   ###########################################################
   # Init object
   ###########################################################
   def init(self):
      # First try
      if self._init() == False:
         # Second try (after token refresh)
         if self._init() == False:
            # Failed permanently
            log.error("ERROR: unable to initialize")
            return False
      return True
      
   ###########################################################
   # Print user info
   ###########################################################
   def printUserInfo(self):
      print("User Info:")
      print("   user:     %s (%s %s)" % (self.__username, self.__user["firstName"], self.__user["lastName"]))
      print("   role:     %s" % self.__user["role"])
      print("   country:  %s" % self.__country)
      if self.__patient is not None:
         print("   patient:  %s (%s %s)" % (self.__patient["username"],self.__patient["firstName"],self.__patient["lastName"]))
            
   ###########################################################
   # Get recent periodic pump data
   ###########################################################
   def getRecentData(self):
      # Check if access token is valid
      if not self._is_token_valid(self.__accessTokenPayload):
         self.__tokenData = self._do_refresh(self.__config, self.__tokenData)
         self.__accessTokenPayload = self._get_access_token_payload(self.__tokenData)
         self._write_token_file(self.__tokenData, self.__tokenFile)
         if not self._is_token_valid(self.__accessTokenPayload):
            log.error("ERROR: unable to get valid access token")
            return None
         
      if self.__patient is not None:
         patientId = self.__patient["username"]
      else:
         patientId = None
      
      # Get data: first try
      data = self._get_data(self.__config,
                            self.__tokenData,
                            self.__username,
                            self.__user["role"],
                            patientId)
      # Check API response
      if self.__last_api_status in AUTH_ERROR_CODES:
         # Try to refresh token
         self.__tokenData = self._do_refresh(self.__config, self.__tokenData)
         self.__accessTokenPayload = self._get_access_token_payload(self.__tokenData)
         self._write_token_file(self.__tokenData, self.__tokenFile)

         # Get data: second try
         data = self._get_data(self.__config,
                               self.__tokenData,
                               self.__username,
                               self.__user["role"],
                               patientId)
         # Check API response
         if self.__last_api_status in AUTH_ERROR_CODES:
            # Failed permanently
            log.error("ERROR: unable to get data")
            return None
      return data

   ###########################################################
   # Get data using web interface API (personalWebView)
   ###########################################################
   def _get_web_data(self, token_data):
      """Get data using the web interface personalWebView endpoint"""
      log.info("_get_web_data() - using personalWebView endpoint")
      url = "https://clcloud.minimed.eu/connect/retina/v1/personalWebView"

      headers = {
         "Accept": "application/json, text/plain, */*",
         "Accept-Language": "en-US,en;q=0.9",
         "Accept-Encoding": "gzip, deflate, br, zstd",
         "Authorization": "Bearer " + token_data["access_token"],
         "Content-Type": "application/json; charset=utf-8",
         "Origin": "https://carelink.minimed.eu",
         "Referer": "https://carelink.minimed.eu/",
         "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
         "Connection": "keep-alive",
         "Sec-Fetch-Dest": "empty",
         "Sec-Fetch-Mode": "cors",
         "Sec-Fetch-Site": "same-site",
         "Pragma": "no-cache",
         "Cache-Control": "no-cache"
      }

      self.__last_api_status = None
      resp = requests.get(url=url, headers=headers)
      self.__last_api_status = resp.status_code
      log.info("   personalWebView API response status: %d" % resp.status_code)

      try:
         my_data = resp.json()

         # Analyze response to see date range
         if my_data and isinstance(my_data, dict):
            # Look for data arrays that might contain timestamped entries
            for key in ['sgs', 'markers', 'readings', 'events', 'data', 'sensorGlucose']:
               if key in my_data and isinstance(my_data[key], list) and len(my_data[key]) > 0:
                  log.info("   Found %d entries in '%s'" % (len(my_data[key]), key))

                  # Try to find date range in the data
                  dates = []
                  for entry in my_data[key][:5]:  # Check first 5 entries
                     if isinstance(entry, dict):
                        for date_field in ['datetime', 'timestamp', 'date', 'time', 'sg_datetime']:
                           if date_field in entry:
                              dates.append(entry[date_field])
                              break

                  if dates:
                     log.info("   Data dates sample: %s" % dates[:3])

            # Check if response includes any date-related metadata
            if 'lastSensorTSAsString' in my_data:
               log.info("   Last sensor timestamp: %s" % my_data['lastSensorTSAsString'])

      except Exception as e:
         log.warning("   Could not parse personalWebView response JSON: %s" % str(e))
         my_data = None

      return my_data

   ###########################################################
   # Get historical data for a date range
   ###########################################################
   def getHistoricalData(self, days_back=7):
      """
      Get historical data for the specified number of days back from today

      Args:
         days_back (int): Number of days back from today to retrieve data (default: 7)

      Returns:
         dict: Historical data from the API, or None on error
      """
      # Check if access token is valid
      if not self._is_token_valid(self.__accessTokenPayload):
         self.__tokenData = self._do_refresh(self.__config, self.__tokenData)
         self.__accessTokenPayload = self._get_access_token_payload(self.__tokenData)
         self._write_token_file(self.__tokenData, self.__tokenFile)
         if not self._is_token_valid(self.__accessTokenPayload):
            log.error("ERROR: unable to get valid access token")
            return None

      if self.__patient is not None:
         patientId = self.__patient["username"]
      else:
         patientId = None

      # Calculate date range
      end_date = datetime.now()
      start_date = end_date - timedelta(days=days_back)

      # Format dates for API (try common formats)
      start_date_str = start_date.strftime("%Y-%m-%d")
      end_date_str = end_date.strftime("%Y-%m-%d")

      log.info("Getting historical data for %d days (%s to %s)" % (days_back, start_date_str, end_date_str))

      # Get data: first try
      data = self._get_data(self.__config,
                            self.__tokenData,
                            self.__username,
                            self.__user["role"],
                            patientId,
                            start_date_str,
                            end_date_str)
      # Check API response
      if self.__last_api_status in AUTH_ERROR_CODES:
         # Try to refresh token
         self.__tokenData = self._do_refresh(self.__config, self.__tokenData)
         self.__accessTokenPayload = self._get_access_token_payload(self.__tokenData)
         self._write_token_file(self.__tokenData, self.__tokenFile)

         # Get data: second try
         data = self._get_data(self.__config,
                               self.__tokenData,
                               self.__username,
                               self.__user["role"],
                               patientId,
                               start_date_str,
                               end_date_str)
         # Check API response
         if self.__last_api_status in AUTH_ERROR_CODES:
            # Failed permanently
            log.error("ERROR: unable to get historical data")
            return None
      return data

   ###########################################################
   # Generate CSV report and get UUID
   ###########################################################
   def _generate_csv_report(self, token_data, start_date=None, end_date=None, days_back=14):
      """Generate a CSV report and return the UUID"""
      log.info("_generate_csv_report() - generating new CSV report")

      url = "https://carelink.minimed.eu/patient/reports/generateReport"

      headers = {
         "Authorization": "Bearer " + token_data["access_token"],
         "Content-Type": "application/json; charset=utf-8",
         "Origin": "https://carelink.minimed.eu",
         "Referer": "https://carelink.minimed.eu/app/reports",
         "Cookie": f"auth_tmp_token={token_data['access_token']}"
      }

      # Calculate date range if not provided
      if not start_date or not end_date:
         from datetime import datetime, timedelta
         end_dt = datetime.now()
         start_dt = end_dt - timedelta(days=days_back)
         start_date = start_dt.strftime("%Y-%m-%d")
         end_date = end_dt.strftime("%Y-%m-%d")

      # Generate current timestamp
      from datetime import datetime
      client_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+02:00")

      # Debug: show available user and patient data
      if self.__user:
         log.info("   User data keys: %s" % list(self.__user.keys()))
         log.info("   User ID: %s" % self.__user.get("id", "NOT_FOUND"))
      if self.__patient:
         log.info("   Patient data keys: %s" % list(self.__patient.keys()))
         log.info("   Patient data: %s" % str(self.__patient))
      else:
         log.warning("   No patient data available")

      # Get patient ID - use numeric ID from user data
      patient_id = self.__username  # fallback to username
      if self.__user and "id" in self.__user:
         patient_id = str(self.__user["id"])  # Use numeric user ID
         log.info("   Found numeric user ID: %s" % patient_id)
      elif self.__patient and "patientId" in self.__patient:
         patient_id = self.__patient["patientId"]
      elif self.__patient and "id" in self.__patient:
         patient_id = self.__patient["id"]

      log.info("   Using patient ID: %s (type: %s)" % (patient_id, type(patient_id)))

      # Request payload based on the user's curl (exact format)
      payload = {
         "clientTime": client_time,
         "dailyDetailReportDays": [],
         "patientId": str(patient_id),
         "reportFileFormat": "CSV",
         "reportShowAdherence": False,
         "reportShowAssessmentAndProgress": False,
         "reportShowBolusWizardFoodBolus": False,
         "reportShowDashBoard": False,
         "reportShowDataTable": False,
         "reportShowDeviceSettings": False,
         "reportShowEpisodeSummary": False,
         "reportShowLogbook": False,
         "reportShowOverview": False,
         "reportShowWeeklyReview": False,
         "reportShowSettingsHistory": False,
         "reportShowInsulinAssessment": False,
         "startDate": start_date,
         "endDate": end_date,
         "aggregatedCsvEnabled": True
      }

      log.info("   Payload: %s" % str(payload)[:200])

      log.info("   Report date range: %s to %s" % (start_date, end_date))

      self.__last_api_status = None
      resp = requests.post(url=url, headers=headers, json=payload)
      self.__last_api_status = resp.status_code
      log.info("   Report generation status: %d" % resp.status_code)

      try:
         if resp.status_code == 200:
            result = resp.json()
            uuid = result.get('uuid')
            if uuid:
               log.info("   ✅ Report generated with UUID: %s" % uuid)
               return uuid
            else:
               log.error("   ❌ No UUID in response: %s" % str(result))
               return None
         else:
            log.error("   Failed to generate report - HTTP %d" % resp.status_code)
            log.error("   Full response: %s" % resp.text)
            return None
      except Exception as e:
         log.error("   Could not parse generation response: %s" % str(e))
         log.error("   Raw response: %s" % resp.text)
         return None


   ###########################################################
   # Check CSV report status
   ###########################################################
   def _check_csv_report_status(self, token_data, report_uuid):
      """Check if CSV report is ready for download"""
      url = f"https://carelink.minimed.eu/patient/reports/reportStatus?uuid={report_uuid}"

      headers = {
         "Authorization": "Bearer " + token_data["access_token"],
         "Referer": "https://carelink.minimed.eu/app/reports",
         "Cookie": f"auth_tmp_token={token_data['access_token']}"
      }

      self.__last_api_status = None
      resp = requests.get(url=url, headers=headers)
      self.__last_api_status = resp.status_code

      try:
         if resp.status_code == 200:
            result = resp.json()
            status = result.get('status', 'UNKNOWN')
            return status
         else:
            log.warning("   Failed to check report status - HTTP %d" % resp.status_code)
            return None
      except Exception as e:
         log.warning("   Could not parse status response: %s" % str(e))
         return None

   ###########################################################
   # Wait for CSV report to be ready
   ###########################################################
   def _wait_for_csv_report(self, token_data, report_uuid, max_wait_seconds=60):
      """Wait for CSV report to be ready, polling every 1 second"""
      import time

      log.info("   Waiting for report to be ready (UUID: %s)" % report_uuid)
      log.info("   Will poll every 1s for up to %ds" % max_wait_seconds)

      start_time = time.time()
      attempt = 0

      while time.time() - start_time < max_wait_seconds:
         attempt += 1
         status = self._check_csv_report_status(token_data, report_uuid)

         if status == "READY":
            log.info("   ✅ Report ready after %d attempts (%.1fs)" % (attempt, time.time() - start_time))
            return True
         elif status == "NOT_READY":
            log.info("   ⏳ Attempt %d: Report not ready yet" % attempt)
         elif status is None:
            log.warning("   ❓ Attempt %d: Could not check status" % attempt)
         else:
            log.info("   📊 Attempt %d: Status = %s" % (attempt, status))

         if time.time() - start_time < max_wait_seconds:
            time.sleep(1)

      log.error("   ⏰ Timeout: Report not ready after %ds" % max_wait_seconds)
      return False

   ###########################################################
   # Download CSV report (historical data)
   ###########################################################
   def _download_csv_report(self, token_data, report_uuid):
      """Download CSV report using the reportCsv endpoint"""
      log.info("_download_csv_report() - downloading report UUID: %s" % report_uuid)
      url = f"https://carelink.minimed.eu/patient/reports/reportCsv?uuid={report_uuid}&dMInFileName=false"

      headers = {
         "Authorization": "Bearer " + token_data["access_token"],
         "Referer": "https://carelink.minimed.eu/app/reports",
         "Cookie": f"auth_tmp_token={token_data['access_token']}"
      }

      self.__last_api_status = None
      resp = requests.get(url=url, headers=headers)
      self.__last_api_status = resp.status_code
      log.info("   CSV report download status: %d" % resp.status_code)
      log.info("   Content type: %s" % resp.headers.get('content-type', 'unknown'))
      log.info("   Content length: %s bytes" % resp.headers.get('content-length', 'unknown'))

      if resp.status_code == 200:
         # Check if it's CSV content
         content_type = resp.headers.get('content-type', '')
         if 'csv' in content_type.lower() or 'text' in content_type.lower():
            log.info("   Successfully downloaded CSV data")
            return resp.text
         else:
            log.info("   Response might be JSON error or other format")
            try:
               # Try to parse as JSON to see if it's an error response
               json_data = resp.json()
               log.info("   JSON response: %s" % str(json_data)[:200])
               return json_data
            except:
               log.info("   Raw response (first 200 chars): %s" % resp.text[:200])
               return resp.text
      else:
         log.error("   Failed to download CSV report - HTTP %d" % resp.status_code)
         # Show the actual error response
         try:
            error_data = resp.json()
            log.error("   Server error: %s" % str(error_data))
         except:
            log.error("   Raw error response: %s" % resp.text[:500])
         return None

   ###########################################################
   # Get data using web interface (more historical data)
   ###########################################################
   def getWebData(self):
      """
      Get data using the web interface personalWebView endpoint
      This might return more historical data than the mobile API

      Returns:
         dict: Data from the web interface API, or None on error
      """
      # Check if access token is valid
      if not self._is_token_valid(self.__accessTokenPayload):
         self.__tokenData = self._do_refresh(self.__config, self.__tokenData)
         self.__accessTokenPayload = self._get_access_token_payload(self.__tokenData)
         self._write_token_file(self.__tokenData, self.__tokenFile)
         if not self._is_token_valid(self.__accessTokenPayload):
            log.error("ERROR: unable to get valid access token")
            return None

      log.info("Getting data from web interface (personalWebView)")

      # Get data: first try
      data = self._get_web_data(self.__tokenData)

      # Check API response
      if self.__last_api_status in AUTH_ERROR_CODES:
         # Try to refresh token
         self.__tokenData = self._do_refresh(self.__config, self.__tokenData)
         self.__accessTokenPayload = self._get_access_token_payload(self.__tokenData)
         self._write_token_file(self.__tokenData, self.__tokenFile)

         # Get data: second try
         data = self._get_web_data(self.__tokenData)

         # Check API response
         if self.__last_api_status in AUTH_ERROR_CODES:
            # Failed permanently
            log.error("ERROR: unable to get web interface data")
            return None
      return data

   ###########################################################
   # Download CSV report with historical data
   ###########################################################
   def getCsvReport(self, report_uuid, wait_if_not_ready=True):
      """
      Download CSV report containing historical data

      Args:
         report_uuid (str): UUID of the report to download (required)
         wait_if_not_ready (bool): Wait for report if not ready (default: True)

      Returns:
         str: CSV data as text, or None on error
      """
      # Check if access token is valid
      if not self._is_token_valid(self.__accessTokenPayload):
         self.__tokenData = self._do_refresh(self.__config, self.__tokenData)
         self.__accessTokenPayload = self._get_access_token_payload(self.__tokenData)
         self._write_token_file(self.__tokenData, self.__tokenFile)
         if not self._is_token_valid(self.__accessTokenPayload):
            log.error("ERROR: unable to get valid access token")
            return None

      if not report_uuid:
         log.error("ERROR: report_uuid is required for CSV download")
         return None

      log.info("Downloading CSV report with UUID: %s" % report_uuid)

      # Check if we should wait for the report to be ready
      if wait_if_not_ready:
         status = self._check_csv_report_status(self.__tokenData, report_uuid)
         if status == "NOT_READY":
            log.info("Report not ready yet, waiting...")
            if not self._wait_for_csv_report(self.__tokenData, report_uuid, max_wait_seconds=60):
               log.error("ERROR: Report not ready after waiting")
               return None
         elif status != "READY" and status is not None:
            log.info("Report status: %s" % status)

      # Download CSV: first try
      data = self._download_csv_report(self.__tokenData, report_uuid)

      # Check API response
      if self.__last_api_status in AUTH_ERROR_CODES:
         # Try to refresh token
         self.__tokenData = self._do_refresh(self.__config, self.__tokenData)
         self.__accessTokenPayload = self._get_access_token_payload(self.__tokenData)
         self._write_token_file(self.__tokenData, self.__tokenFile)

         # Download CSV: second try
         data = self._download_csv_report(self.__tokenData, report_uuid)

         # Check API response
         if self.__last_api_status in AUTH_ERROR_CODES:
            # Failed permanently
            log.error("ERROR: unable to download CSV report")
            return None
      return data


   ###########################################################
   # Generate and download CSV report
   ###########################################################
   def generateAndDownloadCsvReport(self, days_back=14):
      """
      Generate a new CSV report and download it immediately

      Args:
         days_back (int): Number of days of historical data to include (default: 14)

      Returns:
         str: CSV data as text, or None on error
      """
      # Check if access token is valid
      if not self._is_token_valid(self.__accessTokenPayload):
         self.__tokenData = self._do_refresh(self.__config, self.__tokenData)
         self.__accessTokenPayload = self._get_access_token_payload(self.__tokenData)
         self._write_token_file(self.__tokenData, self.__tokenFile)
         if not self._is_token_valid(self.__accessTokenPayload):
            log.error("ERROR: unable to get valid access token")
            return None

      log.info("Generating and downloading CSV report for %d days" % days_back)

      # Step 1: Generate report and get UUID
      uuid = self._generate_csv_report(self.__tokenData, days_back=days_back)
      if not uuid:
         log.error("ERROR: Could not generate CSV report")
         return None

      log.info("Report UUID: %s" % uuid)

      # Step 2: Wait for report to be ready
      if not self._wait_for_csv_report(self.__tokenData, uuid, max_wait_seconds=60):
         log.error("ERROR: Report generation timed out")
         return None

      # Step 3: Download the report using the UUID
      # Download CSV: first try
      data = self._download_csv_report(self.__tokenData, uuid)

      # Check API response
      if self.__last_api_status in AUTH_ERROR_CODES:
         # Try to refresh token
         self.__tokenData = self._do_refresh(self.__config, self.__tokenData)
         self.__accessTokenPayload = self._get_access_token_payload(self.__tokenData)
         self._write_token_file(self.__tokenData, self.__tokenFile)

         # Download CSV: second try
         data = self._download_csv_report(self.__tokenData, uuid)

         # Check API response
         if self.__last_api_status in AUTH_ERROR_CODES:
            # Failed permanently
            log.error("ERROR: unable to download generated CSV report")
            return None

      return data

   ###########################################################
   # Get last API response code
   ###########################################################
   def getLastResponseCode(self):
      return self.__last_api_status
   
   ###########################################################
   # Get Client library version
   ###########################################################
   def getClientVersion(self):
      return self.__version
