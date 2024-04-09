import requests
import pprint

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
**Rapture Level:** {character["character_info"]["raptureLevel"]}
**Ranking:** {character["ranking"]}
**Leaderboard:** {character["leaderboard_type"]}
**Status:** {alive_status}
**ID:** {character["character_info"]["id"]}
\n"""
        else:
            message += f"""**Name:** {character["character_info"]["name"]}
**Rapture Level:** {character["character_info"]["raptureLevel"]}
**Ranking:** {character["ranking"]}
**Leaderboard:** {character["leaderboard_type"]}
**ID:** {character["character_info"]["id"]}
\n"""
    return message


def leaderboard_lookup(username: str, info_details: str = None) -> str:
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
