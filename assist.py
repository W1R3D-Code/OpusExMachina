import sys
from dotenv import load_dotenv
import json
import openai
import os
import random
import re
from typing import Dict, List
from varname import nameof

with open("config.json") as f:
    config = json.load(f)

def is_valid_model(id: str) -> bool:
    response = openai.Model.list()
    return response is not None and id in [model['id'] for model in response['data']] # type: ignore

def validate_openai_config(model_id: str) -> None:
    if openai.organization is None:
        print(f"Error: {nameof(openai)}.{nameof(openai.organization)} is not set.")
        exit(1)
    if openai.api_key is None:
        print(f"Error: {nameof(openai)}.{nameof(openai.api_key)} is not set.")
        exit(1)
    if not is_valid_model(model_id):
        print(f"Error: '{model_id}' is not a valid model.")
        exit(1)

def get_system_commands(system_name: str, system_commands: list[str]) -> list[dict[str, str]]:
    system_commands = [cmd.format(system_name=system_name) for cmd in system_commands]
    return [{"role": "system", "content": "\n".join(system_commands)}]

def print_system_response(system_name: str, response_content: str, pad: int) -> None:
    """
    Prints the personal assistant's response.

    Args:
        system_name (str): The username of the personal assistant.
        response_content (str): The response content to print.
        pad (int): The padding to use for formatting the response.
    """
    reset_colour = "\033[0m"
    sys_colour = '\033[38;2;0;191;255m'  # medium light blue
    response_colour = '\033[38;2;153;204;255m'  # slightly lighter shade of blue
    sys_prompt = f"{sys_colour}{(system_name + ':').ljust(pad, ' ')}{response_colour}"

    print()
    print(f"{sys_prompt}{response_content}{reset_colour}")

def get_user_input(username: str, pad: int) -> str:
    """
    Prompts the user for input and returns the input as a string.

    Args:
        username (str): The username of the user.
        pad (int): The number of characters to pad the username with.

    Returns:
        str: The input from the user.
    """
    reset_colour = "\033[0m"
    usr_prompt_color = "\033[38;2;109;154;100m" # light forest green
    input_color = "\033[38;2;143;181;137m" # slightly lighter than light forest green
    usr_prompt = f"{usr_prompt_color}{(username + ':').ljust(pad, ' ')}{input_color}"

    print()
    prompt = input(usr_prompt)
    print(reset_colour, end='')

    return prompt

def start_conversation(model_id: str, user_name: str, system_name: str, system_commands: list[str]) -> List[Dict[str, str]]:
    """
    Start a conversation with the personal assistant.

    Args:
        model_id (str): The ID of the OpenAI language model to use for the conversation.
        username (str): The name of the user initiating the conversation.
        system_name (str): The name of the personal assistant.
        system_commands (list[str]): Array of strings to give the language model as system commands
    """
    messages = get_system_commands(system_name, system_commands)
    pad = max(len(system_name), len(user_name)) + 2

    print_system_response(system_name, f"How can I help you {user_name}?", pad)

    try:
        while True:
            prompt = get_user_input(user_name, pad)

            if not prompt or re.match(r'^((?:exit|quit|q)(\(\))?[;]?[\W]*)$', prompt, re.IGNORECASE):
                break
            elif re.match(r'^((?:help)(\(\))?[;]?[\W]*)$', prompt, re.IGNORECASE):
                messages.append({"role": "user", "content": "How can you help me?"})
            else:
                messages.append({"role": "user", "content": prompt})

            response = openai.ChatCompletion.create(
                model=model_id,
                messages=messages
            )

            response_content = response['choices'][0]['message']['content'] # type: ignore
            messages.append({"role": "assistant", "content": response_content})
            print_system_response(system_name, response_content, pad)


    except (KeyboardInterrupt, SystemExit):
        print('\033[31m' + "\nExiting..." + '\033[0m')
    except Exception as e:
        print('\033[31m' + f"\nError: {e}" + '\033[0m')
    finally:
        return messages


if not sys.stdin.isatty():
    exit(1)

load_dotenv()

openai.organization = config.get("org_id", os.getenv("OPENAI_ORG"))
openai.api_key = config.get("api_key", os.getenv("OPENAI_KEY"))

model_id = config.get("model_id", os.getenv("OPENAI_MODEL"))

validate_openai_config(model_id)

system_commands = config.get("system_commands")
sys_names = config.get("system_names", ["System"])
system_name = random.choice(sys_names)

username = config.get("user_name", "User")

# TODO:: load message history from saved convo
messages = start_conversation(model_id, username, system_name, system_commands)
# TODO:: save message history to json/jsonl