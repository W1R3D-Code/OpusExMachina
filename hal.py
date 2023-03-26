import os
import openai
import re

from pprint import pprint

openai.organization = os.getenv("OPENAI_ORF")
openai.api_key = os.getenv("OPENAI_KEY")

model_engine = 'gpt-3.5-turbo'
messages=[
        {"role": "system", "content": "You are a helpful assistant called HAL 9000, or HAL for short. Answer as accurately & concisely as possible while prioritising facts. At the end of every response summarise any assumptions & speculation in your answer. Always respond in markdown."},
    ]

print("How can I help you?\n")

while True:
    prompt = input("User\n\t>\t")
    
    if re.match(r'((?:exit|quit)(\(\))?[;]?)', prompt, re.IGNORECASE):
        break
    elif re.match(r'((?:help)(\(\))?[;]?)', prompt, re.IGNORECASE):
        print("Just enter some text.")
    else:
        messages.append({"role": "user", "content": prompt})

        response = openai.ChatCompletion.create(
            model=model_engine,
            messages=messages
        )

        response_content = response['choices'][0]['message']['content']
        messages.append({"role": "assistant", "content": response_content})

        print("\nHAL\n\t>\t")
        print(response_content)
        print("\n")
