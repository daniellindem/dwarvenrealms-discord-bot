import requests
import yaml
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Load the environment variables

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DISCORD_BOT_APPLICATION_ID = os.getenv('DISCORD_BOT_APPLICATION_ID')
URL = f"https://discord.com/api/v10/applications/{DISCORD_BOT_APPLICATION_ID}/commands"
headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"}

def cleanup_commands():
    active_commands = requests.get(URL, headers=headers)
    for command in active_commands.json():
        command_id = command["id"]
        response = requests.delete(f"{URL}/{command_id}", headers=headers)
        print(f"Command {command_id} deleted: {response.status_code}")


def add_commands():
   with open("discord_commands.yaml", "r") as file:
    yaml_content = file.read()

    commands = yaml.safe_load(yaml_content)

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


def main():
    cleanup_commands()
    add_commands()
    
if __name__ == "__main__":
    main()