import azure.functions as func
import requests
import logging
import os
import math
import json
from discord_interactions import verify_key
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


DISCORD_BOT_PUBLIC_KEY = os.getenv('DISCORD_BOT_PUBLIC_KEY')
HANDLER_FUNCTION_KEY = os.getenv('HANDLER_FUNCTION_KEY')
INTERACTION_FUNCTION_KEY = os.getenv('INTERACTION_FUNCTION_KEY')
AZFUNC = os.getenv('AZFUNC')
GOOGLE_API_SPREADSHEET_ID = os.getenv("GOOGLE_API_SPREADSHEET_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# BASE FUNCTION FUNCTIONS
def signature_verification(req: func.HttpRequest) -> bool:
    try:
        signature = req.headers.get("X-Signature-Ed25519")
        timestamp = req.headers.get("X-Signature-Timestamp")
        body = req.get_body()
        
        if signature and timestamp and body:
            if verify_key(body, signature, timestamp, DISCORD_BOT_PUBLIC_KEY):
                logging.info("Discord signature has been verified.")
                return True
            else:
                logging.error("Signature is invalid")
                return False
        else:
            #logging.error("Missing required headers or body.")
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
    logging.info (f"Creating HTTP response with status code {status_code}")
    return func.HttpResponse(json.dumps(content), status_code=status_code, mimetype=mimetype)

# ----------------------------------------------------------------------------
# ---------------------------- BASE FUNCTION ---------------------------------
# ----------------------------------------------------------------------------

app = func.FunctionApp()
@app.route(route="dr_discord_bot_handler", auth_level=func.AuthLevel.FUNCTION)
@app.queue_output(arg_name="interactionbody", 
                  queue_name="interactionqueue", 
                  connection="AzureWebJobsStorage")
def dr_discord_bot_handler(req: func.HttpRequest, interactionbody: func.Out [func.QueueMessage]) -> func.HttpResponse:
    #try:
    logging.info('Python HTTP trigger function processed a request.')
    
    # Verify request signature
    if req.get_json()['type'] == 'warmup':
        logging.info('Received warmup request.')
        response = 'Warmed up'
        status_code = 200
        return create_http_response(response, status_code)
    elif not signature_verification(req):
        logging.warning("Invalid request signature")
        return create_http_response("Invalid request signature", 401)

    req_body = req.get_json()
    #logging.debug(f"Request body: {req_body}")

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
        #logging.warning(f"Requesting URL: {url}") # Potentially sensitive

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    #except Exception as e:
        #logging.error(f"Unexpected error in base function: {e}")
        #return create_http_response("Internal server error", 500)
        
        try:
            print(url)
            #res = requests.post(url, headers=headers, json=req_body, timeout=1)
            interactionbody.set(json.dumps(req_body))
            #res.raise_for_status()
            #logging.info(f"Response status code: {res.status_code}")
        except requests.exceptions.RequestException as e:
            logging.warning(f"Request either timed out like expected or something else happened: {e}")
        except Exception as e:
            logging.error(f"Unexpected error in base function: {e}")
            #return create_http_response("Internal server error", 500)
    return create_http_response(response, status_code)
    


# INTERACTION FUNCTION FUNCTIONS


def rupturecalc(rupturelevel, rerollcost):
    spreadsheet_range = "Rupture Boss Chest Calculated Data!A1:H"
    spreadsheet_url = f"https://sheets.googleapis.com/v4/spreadsheets/{GOOGLE_API_SPREADSHEET_ID}/values/{spreadsheet_range}?key={GOOGLE_API_KEY}"
    
    try:
        # Call the Sheets API
        result = requests.get(url=spreadsheet_url)
        values = result.json().get("values", [])
        
        if not values:
            logging.warning("No data found in sheet.")
            return "No data found in sheet."
        
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
            return f"Rupture level {rupturelevel} not found in the spreadsheet."
            
    except requests.HTTPError as httperr:
        logging.error(f"HTTP error occurred: {httperr}")
        return f"HTTP error occurred: {httperr}"
    except Exception as e:
        logging.error(f"Error occurred in rupturecalc: {e}")
        return f"Error occurred in rupturecalc: {e}"
    
def get_user_characters(username: str):
    # URLs for normal and hardcore leaderboards
    softcore_url = "http://loadbalancer-e2a9b2a-1115437761.us-east-1.elb.amazonaws.com/leaderboards/scores?type=normal"
    hardcore_url = "http://loadbalancer-e2a9b2a-1115437761.us-east-1.elb.amazonaws.com/leaderboards/scores?type=hardcore"

    # Make requests to both URLs
    softcore_response = requests.get(softcore_url)
    hardcore_response = requests.get(hardcore_url)

    username_lower = username.lower()

    # Check if requests were successful
    if softcore_response.status_code == 200 and hardcore_response.status_code == 200:
        # Parse JSON responses
        softcore_data = softcore_response.json()
        hardcore_data = hardcore_response.json()

        user_info_list = []
        sc_ranking = 1
        hc_ranking = 1

        # Search for username in normal leaderboard
        for leaderboard in softcore_data["leaderboards"]:
            if str(leaderboard["name"].split()[0]).lower() == username_lower:
                user_info_list.append({"leaderboard_type": "Softcore", "character_info": leaderboard, "ranking": sc_ranking})
            sc_ranking += 1

        # Search for username in hardcore leaderboard
        for leaderboard in hardcore_data["leaderboards"]:
            if str(leaderboard["name"].split()[0]).lower() == username_lower:
                user_info_list.append({"leaderboard_type": "Hardcore", "character_info": leaderboard, "ranking": hc_ranking})
            hc_ranking += 1

        if user_info_list:
            return user_info_list
        else:
            return f"No characters found for user '{username}' in leaderboards."
    else:
        return "Failed to retrieve leaderboard data."
    

    
def format_character_info_base(highest_characters):
    highest_characters_sorted = sorted(highest_characters, key=lambda x: int(x["character_info"]["raptureLevel"]), reverse=True)
    #print(highest_characters_sorted)
    message = ""
    for character in highest_characters_sorted:
        if character["leaderboard_type"] == "Hardcore":
            if character["character_info"]["deaths"] == "0":
                alive_status = "Alive"
            else:
                alive_status = "Dead"
            message += f"""**Name:** {character["character_info"]["name"]}
**Rupture Level:** {character["character_info"]["raptureLevel"]}
**Ranking:** {character["ranking"]}
**Leaderboard:** {character["leaderboard_type"]}
**Status:** {alive_status}
\n"""
        else:
            message += f"""**Name:** {character["character_info"]["name"]}
**Rupture Level:** {character["character_info"]["raptureLevel"]}
**Ranking:** {character["ranking"]}
**Leaderboard:** {character["leaderboard_type"]}
\n"""
    return message


def leaderboard_lookup(username: str, info_details: str = None) -> str:
    """
    Looks up the leaderboard information for a given username.

    Args:
        username (str): The username to lookup.
        info_details (str, optional): Additional information details. Defaults to None. (Not implemented)

    Returns:
        str: The formatted character information.
    """
    user_characters = get_user_characters(username)
    
    highest_hc = None
    highest_hc_alive = None
    highest_sc = None
    for character in user_characters:
        if character["leaderboard_type"] == "Softcore" and (highest_sc is None or int(character["character_info"]["raptureLevel"]) > int(highest_sc["character_info"]["raptureLevel"])):
            highest_sc = character
        elif character["leaderboard_type"] == "Hardcore":
            if highest_hc is None or int(character["character_info"]["raptureLevel"]) > int(highest_hc["character_info"]["raptureLevel"]):
                highest_hc = character
            if character["character_info"]["deaths"] == '0' and (highest_hc_alive is None or int(character["character_info"]["rating"]) > int(highest_hc_alive["character_info"]["rating"])):
                highest_hc_alive = character

    highest_characters = []
    if highest_sc:
        highest_characters.append(highest_sc)
    if highest_hc and highest_hc_alive and highest_hc['character_info']['id'] == highest_hc_alive['character_info']['id']:
        highest_characters.append(highest_hc_alive)
        return format_character_info_base(highest_characters)
    if highest_hc:
        highest_characters.append(highest_hc)
    if highest_hc_alive:
        highest_characters.append(highest_hc_alive)
    if not info_details:
        message = format_character_info_base(highest_characters)
        #print(message)
        return message
        
def send_discord_followup(request_body, content):
    """
    Sends a follow-up message to a Discord channel.

    Args:
        request_body (dict): The request body containing the application ID and token.
        content (str): The content of the follow-up message.

    Returns:
        str: The response message indicating the success or failure of sending the follow-up message.
    """
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
        logging.info(f"Content: {content}")
        logging.info(f"Body: {body}")

        # Check for HTTP errors
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending Discord follow-up: {e}")
        return f"Error sending Discord follow-up: {e}"
        
        
def interact(raw_request):
    try:
        logging.info("Processing body: %s", raw_request)
        data = raw_request.get("data", {})
        command_name = data.get("name", "")

        match command_name:
            case "github":
                message_content = "[Github Repo](https://github.com/daniellindem/dwarvenrealms-discord-bot)"

            case "leaderboard":
                try:
                    data_options = data.get("options", [{}])
                    logging.debug(f"Data options: {data_options}")
                    username = data_options[0].get("value", "")
                    if len(data_options) > 1:
                        info_details = data_options[1].get("value", None)
                        message_content = leaderboard_lookup(username, info_details)
                    else:
                        message_content = leaderboard_lookup(username)
                except:
                    message_content = "[Leaderboard](https://dwarvenleaderboard.com/)"

            case "help":
                try:
                    sub_command = data.get("options", [{}])[0].get("value", "")
                    if sub_command == "rupturecalc":
                        message_content = "Use `/rupturecalc` followed by the Rupture level and reroll cost to calculate the number of runs needed for the given level and cost."
                    else:
                        message_content = f"Available commands: `help`, `spreadsheet`, `rupturecalc`.\n\n"
                except:
                    message_content = f"Available commands: `help`, `spreadsheet`, `rupturecalc`.\n\n"

            case "spreadsheet":
                message_content = "[Rupture Spreadsheet](https://docs.google.com/spreadsheets/d/1rRO1LMt1NgykrdEfoZdEwhp4c9TRHTexYLuk6mgxLa0/edit#gid=0)"
                
            case "rupturecalc":
                rupturelevel = data.get("options", [{}])[0].get("value", "")
                try:
                    rerollcost = data.get("options", [{}])[1].get("value", 1500)
                except:
                    rerollcost = 1500
                message_content = rupturecalc(rupturelevel, rerollcost)
                
            case _:
                message_content = "Unknown command"


        logging.info(f"Message content: {message_content}")
        return message_content

    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return f"Error processing request: {e}"

# ----------------------------------------------------------------------------
# ------------------------ INTERACTION FUNCTION ------------------------------
# ----------------------------------------------------------------------------
#@app.route(route="dr_discord_bot_interaction_handler", auth_level=func.AuthLevel.FUNCTION)
@app.queue_trigger(arg_name="azqueue", queue_name="interactionqueue",
                               connection="AzureWebJobsStorage") 
def dr_discord_bot_interaction_handler(azqueue: func.QueueMessage):
    try:
        logging.info('Python HTTP trigger function processed a request.')

        #warmup = req.params.get('warmup')
        #if warmup:
        #    logging.info('Received warmup request.')
        #    return create_http_response('Warmed up', status_code=200)

        #raw_req = req.get_json()
        
        raw_req = json.loads(azqueue.get_body().decode('utf-8'))
        #logging.info(f"Received request body: {raw_req}")

        content = interact(raw_req)
        logging.info(f"Interaction result: {content}")

        send_discord_followup(raw_req, content)
        logging.info('Follow-up sent successfully.')

        #return create_http_response("OK", status_code=200)

    except Exception as e:
        logging.error(f"An unexpected error occurred in interaction function: {e}")
        #return create_http_response("Error in interaction function: {e}. Status Code:", status_code=200)
        #return create_http_response("Internal server error", status_code=500)


# ----------------------------------------------------------------------------
# ------------------------ TIMER TRIGGER FUNCTION ----------------------------
# ----------------------------------------------------------------------------
@app.timer_trigger(schedule="0 */3 * * * *", arg_name="myTimer", run_on_startup=True,
              use_monitor=False) 
def ping_discordbot_functions(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.warning('The timer is past due!')

    logging.info('Python timer trigger function executed.')

    body = {"type": "warmup"}
    
    #func1_url = f"{AZFUNC}/api/dr_discord_bot_handler?code={HANDLER_FUNCTION_KEY}"
    func2_url = f"{AZFUNC}/api/dr_discord_bot_interaction_handler?code={INTERACTION_FUNCTION_KEY}&warmup='true'"
    
    headers = {"Content-Type": "application/json"}

    #response1 = requests.post(func1_url, json=body, headers=headers)
    #response2 = requests.post(func2_url, headers=headers)

    #logging.info(f"Response from func1: {response1.status_code}")
    #logging.info(f"Response from func2: {response2.status_code}")