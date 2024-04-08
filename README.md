# Dwarvenrealms Discord Bot

[![Build Status](https://img.shields.io/travis/daniellindem/dwarvenrealms-discord-bot.svg?style=flat-square)](https://travis-ci.org/daniellindem/dwarvenrealms-discord-bot)
[![License](https://img.shields.io/github/license/daniellindem/dwarvenrealms-discord-bot.svg?style=flat-square)](https://github.com/daniellindem/dwarvenrealms-discord-bot/blob/master/LICENSE)

## Overview

This is a serverless Discord bot written in Python and running on Azure Functions. It provides various features and functionalities to enhance your Discord server experience.

## Prerequisites

- Python 3.11
- Azure Functions Core Tools
- Azure subscription
- [Discord application bot](https://discord.com/developers/applications/)

## Getting Started

1. Clone the repository:

    ```bash
    git clone https://github.com/daniellindem/dwarvenrealms-discord-bot.git
    ```

2. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Configure your Azure Functions environment:

    - Create an Azure Functions app in the Azure portal.
    - Set up the necessary environment variables in your Azure Functions app settings.

4. Deploy the bot to Azure Functions:

    For detailed instructions on developing and deploying Azure Functions using Visual Studio Code, you can refer to the [Microsoft Learn guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-develop-vs-code?tabs=node-v4%2Cpython-v2%2Cisolated-process&pivots=programming-language-python).

5. Invite the bot to your Discord server:

    - Create a new Discord application and bot in the Discord Developer Portal.
    - Generate a bot token and copy it.
    - Use the bot token to generate an invite link and invite the bot to your server.

## License

This project is licensed under the [MIT License](LICENSE).