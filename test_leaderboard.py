import requests

def get_user_info(username: str):
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
                return user_info_list
            sc_ranking += 1

        # Search for username in hardcore leaderboard
        for leaderboard in hardcore_data["leaderboards"]:
            if str(leaderboard["name"].split()[0]).lower() == username_lower:
                user_info_list.append({"leaderboard_type": "Hardcore", "character_info": leaderboard, "ranking": hc_ranking})
                if leaderboard['deaths'] == '0':
                    user_info_list = [{"leaderboard_type": "Hardcore", "character_info": leaderboard, "ranking": hc_ranking}]
                    return user_info_list
            hc_ranking += 1

        if user_info_list:
            return user_info_list[0]
        else:
            return f"No characters found for user '{username}' in leaderboards."
    else:
        return "Failed to retrieve leaderboard data."
    
def format_character_info(info):
    character_info = info['character_info']
    # Format tokens list
    tokens_list = '\n'.join([f"- {token}" for token in character_info['tokens']])
    
    # Format build dictionary
    build_info = '\n'.join([f"- **{key} Mod:** {value}" for key, value in character_info['build'].items()])
    
    # Construct the Discord markdown message
    discord_message = f"""**Name:** {character_info['name']}
**Rapture Level:** {character_info['raptureLevel']}
**Ranking:** {info['ranking']}
**Leaderboard:** {info['leaderboard_type']}

**More Information:**
**Character Info:**
- **Level:** {character_info['level']}
- **Deaths:** {character_info['deaths']}
- **Zone:** {character_info['zone']}
- **Stance:** {character_info['stance']}
- **Is Hardcore:** {'Yes' if character_info['isHardcore'] else 'No'}

**Tokens:**
{tokens_list}

**Build:**
{build_info}
"""

    return discord_message


# Example usage
username = "Magy"  # Input username here
user_info = get_user_info(username)
for info in user_info:
    print(info)
    #print(f"Leaderboard Type: {info['leaderboard_type']}")
    #print(info["character_info"])
    leaderboard = info['leaderboard_type']
    character_info = info['character_info']
    ranking = info['ranking']
    #print()
    if leaderboard == 'Hardcore' and character_info['deaths'] == '1':
        deadchar = ' (DEAD)'
    else:
        deadchar = ''
    print(f"Character: {character_info['name']}{deadchar}\nRank: {ranking}\nLeaderboard: {leaderboard}\nMax rapture: {character_info['raptureLevel']}\nLevel: {character_info['level']}, Deaths: {character_info['deaths']}\n\n")
    
    #print("\n\n\n\n\n\n")
    #print(format_character_info(info))
