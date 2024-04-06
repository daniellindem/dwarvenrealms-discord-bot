import requests
import yaml
import os
import sys
from dotenv import load_dotenv

load_dotenv()
print (os.environ)

# Load the environment variables

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DISCORD_BOT_APPLICATION_ID = os.getenv('DISCORD_BOT_APPLICATION_ID')
URL = f"https://discord.com/api/v10/applications/{DISCORD_BOT_APPLICATION_ID}/commands"
print(DISCORD_BOT_APPLICATION_ID)

with open("discord_commands.yaml", "r") as file:
    yaml_content = file.read()

commands = yaml.safe_load(yaml_content)
headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"}

commands_to_delete = ['echo', 'hello']

# Send the POST request for each command
for command in commands:
    try:
        response = requests.post(URL, json=command, headers=headers)
        response.raise_for_status()
        print(response)
    except Exception as e:
        print(f"Failed: {response.status_code} Exception: {e}")
    command_name = command["name"]
    print(f"Command {command_name} created: {response.status_code}")