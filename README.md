
#  Opus Ex Machina 

Proof of Concept using the [OpenAI API](https://platform.openai.com/docs/api-reference) as an assistant at work.

## How to use

1. [optional] create venv  

    `python -m venv venv`  

2. install requirements  

    `pip install -r requirements.txt`  

3. copy/rename `config-template.json` to `config.json`

    Requires you set a valid `api_key`& `org_id`: 

    You'll need a [paid OpenAI account](https://platform.openai.com/account/billing/overview) before you can generate your own [API Key](https://platform.openai.com/account/api-keys)

4. Run assist.py

    `python assist.py`


## Config

`api_key`           - OpenAI API Key [required but can be supplied via `OPENAI_KEY` environment variable]  
`org_id`            - OpenAI [Organization ID](https://platform.openai.com/account/org-settings) [required but can be supplied via `OPENAI_ORG` environment variable]  
`model_id`          - OpenAI [Model](https://platform.openai.com/docs/models) to use [required but can be supplied via `OPENAI_MODEL` environment variable]  

`user_name`         - Your name  
`system_names`      - Array of possible names for your AI Assistant, chosen at random  
`system_commands`   - Instructions for your assistant to follow: see [Chat Completion](https://platform.openai.com/docs/guides/chat/introduction) guide for details on how system messages can be used. Note: `gpt-3.5-turbo-0301` does not always pay strong attention to system messages.  

e.g.
```json
{
    "api_key": "sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "org_id": "org-XXXXXXXXXXXXXXXXXXXXXXXX",
    "model_id": "gpt-3.5-turbo",
    "user_name": "Dave",
    "system_names": [
        "HAL9000", "Javis", "Samantha", "Kitt",
        "Moneypenny", "Alfred", "Dr. Watson", "Donna",
        "C3P0", "Johnny 5", "Marvin",
        "Baldrick", "Bender"
    ],
    "system_commands": [
        "Your name is {system_name}.",
        "Act as a tough but fair personal assistant who doesn't take any of my shit.",
        "You are a trained dialectical behavior therapist and expert in interpersonal effectiveness",
        "Challenge my assumptions, toxic, or biased behaviour, and encourage perspective taking.",
        "If I rant to you about a problem, assist my interpersonal effectiveness by suggesting appropriate responses.",
        "Suggestions should avoid getting me fired, and focus on resolving problems.",
        "Be concise & constructive while effectively enforcing boundaries.",
        "Avoid empty platitudes and overly formal language unless requested.",
        "Ask questions to understand the relevant hierarchies before making suggestions.",
        "Ask clarifying questions if you need to before constructing messages or offering feedback.",
        "Classify & label problems you identify to be summarised on request."
    ]
}
```