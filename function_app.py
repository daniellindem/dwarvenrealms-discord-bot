import azure.functions as func
import requests
import logging
import os
import json
from discord_interactions import verify_key
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google.oauth2 import credentials

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


DISCORD_PUBLIC_KEY = os.getenv('DISCORD_PUBLIC_KEY')
HANDLER_FUNCTION_KEY = os.getenv('HANDLER_FUNCTION_KEY')
INTERACTION_FUNCTION_KEY = os.getenv('INTERACTION_FUNCTION_KEY')
AZFUNC = os.getenv('AZFUNC')
GOOGLE_API_SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GOOGLE_API_CLIENT_ID = os.getenv("CLIENT_ID")
GOOGLE_API_CLIENT_SECRET = os.getenv("CLIENT_SECRET")
GOOGLE_API_REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# BASE FUNCTION FUNCTIONS
def signature_verification(req: func.HttpRequest) -> bool:
    try:
        signature = req.headers.get("X-Signature-Ed25519")
        timestamp = req.headers.get("X-Signature-Timestamp")
        body = req.get_body()
        
        if signature and timestamp and body:
            if verify_key(body, signature, timestamp, DISCORD_PUBLIC_KEY):
                logging.info("Discord signature has been verified.")
                return True
            else:
                logging.error("Signature is invalid")
                return False
        else:
            logging.error("Missing required headers or body.")
            return False
    except Exception as e:
        logging.error(f"Error verifying signature: {e}")
        return False

def validate_headers(req: func.HttpRequest):
    try:
        signature_ed25519 = req.headers.get("X-Signature-Ed25519")
        signature_timestamp = req.headers.get("X-Signature-Timestamp")

        if not signature_ed25519 or not signature_timestamp:
            logging.warning("Missing signature headers.")
            return func.HttpResponse("No signature headers", status_code=401)
        
        # Additional validation checks can be added here if needed
        
        return None  # Headers are valid
    except Exception as e:
        logging.error(f"Error validating headers: {e}")
        return func.HttpResponse("Internal server error", status_code=500)

def create_http_response(content, status_code, mimetype="application/json"):
    return func.HttpResponse(json.dumps(content), status_code=status_code, mimetype=mimetype)

app = func.FunctionApp()
@app.route(route="dr_discord_bot_handler", auth_level=func.AuthLevel.FUNCTION)
def dr_discord_bot_handler(req: func.HttpRequest) -> func.HttpResponse:
    try:
        logging.info('Python HTTP trigger function processed a request.')
        
        # Verify request signature
        if req.get_json()['type'] == 'warmup':
            response = 'Warmed up'
            status_code = 200
            return create_http_response(response, status_code)
        elif not signature_verification(req):
            logging.warning("Invalid request signature")
            return create_http_response("Invalid request signature", 401)

        req_body = req.get_json()
        logging.debug(f"Request body: {req_body}")

        if req_body["type"] == 1:
            response = {"type": 1}
            status_code = 200
        elif req_body["type"] == 2:
            logging.info("Type 2, submitting to queue and deferring")
            response = {
                "type": 5,
                "content": "Pending"
            }
            status_code = 200
            url = f"{AZFUNC}/api/dr_discord_bot_interaction_handler?code={INTERACTION_FUNCTION_KEY}"
            logging.warning(f"Requesting URL: {url}")

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            try:
                res = requests.post(url, headers=headers, json=req_body, timeout=1)
                res.raise_for_status()
            except requests.exceptions.RequestException as e:
                logging.error(f"Error submitting to queue: {e}")
                #return create_http_response("Error submitting to queue", 500)

        return create_http_response(response, status_code)

    except Exception as e:
        logging.error(f"Unexpected error in base function: {e}")
        return create_http_response("Internal server error", 500)


# INTERACTION FUNCTION FUNCTIONS

def get_credentials():
    try:
        # Create GoogleCredentials object
        cred = credentials.Credentials(
            token=None,
            refresh_token=GOOGLE_API_REFRESH_TOKEN,
            token_uri="https://accounts.google.com/o/oauth2/token",
            client_id=GOOGLE_API_CLIENT_ID,
            client_secret=GOOGLE_API_CLIENT_SECRET
        )
        logging.info("Credentials for Google Sheet fetched")
        return cred
    except Exception as e:
        logging.error(f"Error fetching credentials: {e}")
        return None

def rupturecalc(rupturelevel, rerollcost, service):
    spreadsheet_range = "Rupture Boss Chest Calculated Data!A1:H"
    
    try:
        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=GOOGLE_API_SPREADSHEET_ID, range=spreadsheet_range).execute()
        values = result.get("values", [])
        
        if not values:
            logging.warning("No data found.")
            return None
        
        for row in values[1:]:
            if int(row[0]) == rupturelevel:
                craftmat_avg_needed = int(row[3])
                time_essence_needed = 100
                
                # Calculate runs for CraftMat Avg
                runs_for_reroll = round(rerollcost / craftmat_avg_needed, 2)
                runs_for_reroll_rounded = math.ceil(runs_for_reroll)
                
                # Calculate runs for Time Essence
                runs_for_beetle = round(time_essence_needed / int(row[5]), 2)
                runs_for_beetle_rounded = math.ceil(runs_for_beetle)
                
                content = (
                    f"Rupture Level {rupturelevel}\n"
                    f"Runs per Beetle: {runs_for_beetle_rounded} ({runs_for_beetle}).\n"
                    f"Runs per reroll given cost {rerollcost}: {runs_for_reroll_rounded} ({runs_for_reroll})"
                )
                
                return content
        else:
            logging.warning(f"Rupture level {rupturelevel} not found in the spreadsheet.")
            return None
            
    except HttpError as err:
        logging.error(f"HTTP error occurred: {err}")
        return None
        
def send_discord_followup(request_body, content):
    try:
        logging.info("Starting to send Discord follow-up")

        # Construct the URL for sending the follow-up message
        url = f"https://discord.com/api/v10/webhooks/{request_body['application_id']}/{request_body['token']}/messages/@original"

        # Define headers and body for the PATCH request
        headers = {'Content-Type': 'application/json'}
        body = json.dumps({"type": 4, "content": content})

        # Send the PATCH request to Discord API
        response = requests.patch(url, headers=headers, data=body)
        logging.info(f"Response status code: {response.status_code}")
        logging.info(f"Response content: {response.text}")
        logging.info(f"URL: {url}")
        logging.info(f"Content: {content}")
        logging.info(f"Body type: {type(body)}")
        logging.info(f"Body: {body}")

        # Check for HTTP errors
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending Discord follow-up: {e}")
        
        
def interact(raw_request):
    try:
        logging.info("Processing body: %s", raw_request)
        data = raw_request.get("data", {})
        command_name = data.get("name", "")

        if command_name == "hello":
            message_content = "Hello there!"
        elif command_name == "echo":
            original_message = data.get("options", [{}])[0].get("value", "")
            message_content = f"Echoing: {original_message}"
        elif command_name == "spreadsheet":
            message_content = "[Rupture Spreadsheet](https://docs.google.com/spreadsheets/d/1rRO1LMt1NgykrdEfoZdEwhp4c9TRHTexYLuk6mgxLa0/edit#gid=0)"
        elif command_name == "rupturecalc":
            rupturelevel = data.get("options", [{}])[0].get("value", "")
            rerollcost = data.get("options", [{}])[1].get("value", 1500)
            message_content = rupturecalc(rupturelevel, rerollcost)
        else:
            message_content = "Unknown command"

        logging.info("Message content: %s", message_content)
        return message_content

    except Exception as e:
        logging.error("Error processing request: %s", e)
        return "Error processing request"

# INTERACTION HANDLER FUNCTION
@app.route(route="dr_discord_bot_interaction_handler", auth_level=func.AuthLevel.FUNCTION)
def dr_discord_bot_interaction_handler(req: func.HttpRequest) -> func.HttpResponse:
    try:
        logging.info('Python HTTP trigger function processed a request.')

        warmup = req.params.get('warmup')
        if warmup:
            logging.info('Received warmup request.')
            return create_http_response('Warmed up', status_code=200)

        raw_req = req.get_json()
        logging.info(f"Received request body: {raw_req}")

        content = interact(raw_req)
        logging.info(f"Interaction result: {content}")

        send_discord_followup(raw_req, content)
        logging.info('Follow-up sent successfully.')

        return create_http_response("OK", status_code=200)

    except Exception as e:
        logging.error(f"An unexpected error occurred in interaction function: {e}")
        return create_http_response("Internal server error", status_code=500)


# TIMER TRIGGER TO KEEP OTHER FUNCTIONS WARM


@app.timer_trigger(schedule="* 5 * * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def ping_discordbot_functions(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.warning('The timer is past due!')

    logging.info('Python timer trigger function executed.')

    body = {"type": "warmup"}
    
    func1_url = f"{AZFUNC}/api/dr_discord_bot_handler?code={HANDLER_FUNCTION_KEY}"
    func2_url = f"{AZFUNC}/api/dr_discord_bot_interaction_handler?code={INTERACTION_FUNCTION_KEY}&warmup='true'"
    
    headers = {"Content-Type": "application/json"}

    response1 = requests.post(func1_url, json=body, headers=headers)
    response2 = requests.post(func2_url, headers=headers)

    logging.info(f"Response from func1: {response1.status_code}")
    logging.info(f"Response from func2: {response2.status_code}")