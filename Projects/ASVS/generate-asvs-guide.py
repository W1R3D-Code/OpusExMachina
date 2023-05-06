
import sys
from dotenv import load_dotenv
import json
import openai
import os
import random
import re
import requests
import subprocess
import requests
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

def fetch_asvs_requirements():
    release_url = "https://api.github.com/repos/OWASP/ASVS/releases/latest"
    response = requests.get(release_url)
    if response.ok:
        assets = response.json()["assets"]
        # default to language `en` since this is what is used in releases
        regex = r"OWASP\.Application\.Security\.Verification\.Standard\.[\d]{1,2}\.[\d]{1,3}\.[\d]{1,4}-en\.json"
        for asset in assets:
            if re.match(regex, asset["name"]):
                download_url = asset["browser_download_url"]
                response = requests.get(download_url)
                if response.ok:
                    return response.json()
                else:
                    break

    # Fall back to known release (latest at time of writing) if API requests fail
    url = "https://github.com/OWASP/ASVS/releases/download/v4.0.3_release/OWASP.Application.Security.Verification.Standard.4.0.3-en.json"
    response = requests.get(url)
    return response.json()

def get_logged_in_username():
    try:
        output = subprocess.check_output(['gh', 'auth', 'status'], stderr=subprocess.STDOUT)
        for line in output.decode().split('\n'):
            if 'Logged in to' in line:
                return line.split()[-2]
        raise Exception('Not logged in to GitHub')
    except subprocess.CalledProcessError as e:
        raise Exception('Error running gh command') from e

def create_repo(output_dir, username, repo_name, err_not_empty=True):
    # check if the repository already exists
    check_repo_cmd = ["gh", "repo", "list", f"{username}", "--json", "name,owner"]
    try:
        list_repos_output = subprocess.run(check_repo_cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error checking for repository '{repo_name}'")
        print(e)
        return
    
    repo_list = json.loads(list_repos_output.stdout.decode())
    
    for repo in repo_list:
        if repo["name"] == repo_name and repo["owner"]["login"] == username:
            print(f"Repository '{repo_name}' already exists.")
            break
    else:
        # create the repository
        try:
            create_repo_cmd = ["gh", "repo", "create", repo_name, "--private"]
            subprocess.run(create_repo_cmd, cwd=output_dir, check=True)
            print(f"Repository '{repo_name}' created.")
        except subprocess.CalledProcessError as e:
            print(f"Error creating repository '{repo_name}'")
            print(e)
            return

    # clone the repository if the folder doesn't exist
    if not os.path.exists(os.path.join(output_dir, repo_name)):
        try:
            clone_repo_cmd = ["gh", "repo", "clone", f"{username}/{repo_name}"]
            subprocess.run(clone_repo_cmd, cwd=output_dir, check=True)
            print(f"Repository '{repo_name}' cloned.")
        except subprocess.CalledProcessError as e:
            print(f"Error cloning repository '{repo_name}'")
            print(e)
            return
    else:
        print(f"Folder '{repo_name}' already exists, skipping cloning.")

    # check if the repo directory is empty
    if err_not_empty and len([f for f in os.listdir(os.path.join(output_dir, repo_name)) if not f.startswith('.') and f != 'README.md']) > 0:
        raise ValueError("The cloned repository directory is not empty")


def create_directory_structure_and_files(output_dir, requirements, docs_dir):

    default_tech_stack = "React frontend, C# RESTful WebAPI backend, either CosmosDB or MS SQL data storage, and a Cloudflare WAF"
    system_commands = config.get("system_commands")
    doc_messages = get_system_commands("ASVS Bot", system_commands)
    docs_dir = os.path.join(output_dir, docs_dir)

    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir)

    name = requirements["ShortName"]
    version = requirements["Version"]
    out_dir = os.path.join(docs_dir, f"{name}_{version}")

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    readme = open(os.path.join(out_dir, "README.md"), "w")
    readme.write("# OWASP ASVS Testing Guide\n  \n")

    readme.write("This guide is designed to help you test a web or mobile app against the OWASP Application Security Verification Standard (ASVS).  \n")
    readme.write("It is divided into different chapters based on the ASVS requirement groups.\n  \n")
    
    readme.write("## Table of Contents\n  \n")

    model_id = config.get("model_id", os.getenv("OPENAI_MODEL"))
    
    chapter_index = 0
    chapter_count = len(requirements["Requirements"])

    for chapter in requirements["Requirements"]:
        chapter_index += 1
        chapter_messages = doc_messages.copy()

        chapter_code = f"{name}V{version}-{chapter['Shortcode'][1:]}"
        chapter_shortCode = chapter['Shortcode']
        chapter_shortName = chapter["ShortName"]

        chapter_name = f"{chapter_shortCode} {chapter_shortName}"
        chapter_file_name = chapter_name.replace(" ", "_")

        print(f"Working on Chapter {chapter_index}/{chapter_count}: {chapter_name}")

        chapter_dir = os.path.join(out_dir, chapter_file_name)

        if not os.path.exists(chapter_dir):
            os.makedirs(chapter_dir)

        readme.write(f"- [{chapter_name}](./{chapter_file_name}/README.md)\n")

        chapter_readme = open(os.path.join(chapter_dir, "README.md"), "w")
        chapter_readme.write(f"# {chapter_name}\n  \n")

        chapter_intro_prompt = f"You are writing a practical Testing Guide for the OWASP {name} v{version}."
        chapter_intro_prompt += f"Produce the Introduction for the high level collection of requirements \"{chapter_name}\" ({chapter_code})."
        chapter_intro_prompt += f"The introduction will be inserted under a markdown header `## Introduction`."

        print(f"Chapter {chapter_index}/{chapter_count}: Generating Intro")
        chapter_messages.append({"role": "user", "content": chapter_intro_prompt})
        chapter_intro_response = openai.ChatCompletion.create(
                        model=model_id,
                        messages=chapter_messages
                    )

        chapter_intro = chapter_intro_response['choices'][0]['message']['content'] # type: ignore
        chapter_messages.append({"role": "assistant", "content": chapter_intro})

        if chapter_intro.startswith("I'm sorry, but as an AI language model"):
            print(f"ERROR: Chapter: {chapter_code} ({chapter_index}/{chapter_count} Intro: {chapter_intro}")
            chapter_intro = "OPENAI_ERROR_INVALID_RESPONSE"
        else:
            chapter_readme.write(f"\n## Introduction\n\n  ")
            chapter_readme.write(f"\n{chapter_intro}  \n\n")
      
        chapter_prereq_prompt = f"Add any further detail that someone following this guide might need at this juncture (related to section: {chapter_name})"
        chapter_prereq_prompt +=", before we start looking at the groups of requirements within this category."

        chapter_prereq_prompt += "\nIf relevant, including a list of any prerequisite tools and any relevant step-by-step instructions for their setup."
        chapter_prereq_prompt += "\nIf relevant, assume a modern web application using modern standards like TLS."
        chapter_prereq_prompt += "\nIf you can, make the example technology agnostic; if you cannot then assume a {default_tech_stack}."
        chapter_prereq_prompt += "Include a markdown second-level heading appropriate for this section of the document."

        print(f"Chapter {chapter_index}/{chapter_count}: Generating Pre-requisites")
        chapter_messages.append({"role": "user", "content": chapter_prereq_prompt})
        chapter_prereq_responses = openai.ChatCompletion.create(
                        model=model_id,
                        messages=chapter_messages
                    )

        chapter_prereq = chapter_prereq_responses['choices'][0]['message']['content'] # type: ignore
        chapter_messages.append({"role": "assistant", "content": chapter_prereq})

        if chapter_prereq.startswith("I'm sorry, but as an AI language model"):
            print(f"ERROR: Chapter: {chapter_code} ({chapter_index}/{chapter_count} Notes: {chapter_prereq}")
            chapter_prereq = "OPENAI_ERROR_INVALID_RESPONSE"
        else:
            chapter_readme.write(f"\n{chapter_prereq}  \n\n")

        chapter_readme.write("## Sections\n  \n")

        section_index = 0
        section_count = len(chapter["Items"])
        for section in chapter["Items"]:
            section_index += 1
            requirement_count = len(section["Items"])

            section_messages = chapter_messages.copy()
            section_code = f"{name}V{version}-{section['Shortcode'][1:]}"
            section_name = f"{chapter_shortCode}.{section['Shortcode'][1:]} {section['Name']}"
            section_file_name = section_name.replace(" ", "_")

            if requirement_count < 1:
                print(f"Skipping placeholder section {section_index}/{section_count}: {section_name}.")
                continue
            else:
                print(f"Working on Section: {section_code} ({section_index}/{section_count}) - {section_name}.")

            chapter_readme.write(f"- [{section_name}](./{section_file_name}.md)\n")

            section_file = open(os.path.join(chapter_dir, f"{section_file_name}.md"), "w")

            # TODO:: Add meta-data via markdown comments incl. ASVS version & req number, and agregated L1/2/3 required status + CWE & NIST references

            section_file.write(f"# {section_name}\n")

            section_intro_prompt = f"You are writing a practical Testing Guide for the OWASP {name} v{version}."
            section_intro_prompt += f"Produce the Introduction for the collection of requirements under \"{section_name}\" (a sub section of {chapter_name})."
            section_intro_prompt += f"The introduction will be inserted under a markdown header `## Introduction`."

            print(f"Section {section_index}/{section_count}: Generating Intro")
            section_messages.append({"role": "user", "content": section_intro_prompt})
            section_intro_response = openai.ChatCompletion.create(
                            model=model_id,
                            messages=section_messages
                        )

            section_intro = section_intro_response['choices'][0]['message']['content'] # type: ignore
            section_messages.append({"role": "assistant", "content": section_intro})

            if section_intro.startswith("I'm sorry, but as an AI language model"):
                print(f"ERROR: Section: {section_code} ({section_index}/{section_count} Intro: {section_intro}")
                section_intro = "OPENAI_ERROR_INVALID_RESPONSE"
            else:
                section_file.write(f"\n## Introduction\n\n  ")
                section_file.write(f"\n{section_intro}  \n\n")

            print(f"Chapter Section {section_index}/{section_count} Generating Pre-requisites")

            section_prereq_prompt = f"Add any further detail that someone following this guide might need at this juncture (related to section: {section_name})"
            section_prereq_prompt +=", before we start looking at specific requirements."

            section_prereq_prompt += "\nIf relevant, including a list of any prerequisites and step-by-step instructions for any setup."
            section_prereq_prompt += "\nIf relevant, assume a modern web application using modern standards like TLS."
            section_prereq_prompt += "\nIf you can, make the example technology agnostic; if you cannot then assume a {default_tech_stack}."
            section_prereq_prompt += "Include a markdown second-level heading appropriate for this section of the document."
            
            section_messages.append({"role": "user", "content": section_prereq_prompt})
            section_prereq_response = openai.ChatCompletion.create(
                            model=model_id,
                            messages=section_messages
                        )

            section_prereq = section_prereq_response['choices'][0]['message']['content'] # type: ignore
            section_messages.append({"role": "assistant", "content": section_prereq})

            if section_prereq.startswith("I'm sorry, but as an AI language model"):
                print(f"ERROR: Section: {section_code} ({section_index}/{section_count} Prereq: {section_prereq}")
                section_prereq = "OPENAI_ERROR_INVALID_RESPONSE"
            else:
                section_file.write(f"\n{section_prereq}  \n\n")

            section_file.write(f"## {section_code} Requirements\n  \n")
            
            requirement_index = 0
            for requirement in section["Items"]:
                requirement_index += 1
                requirement_messages = section_messages.copy()
                requirement_id = requirement['Shortcode']
                requirement_code = f"{name}V{version}-{requirement_id[1:]}"
                requirement_description = requirement['Description']

                print(f"Working on Requirement {requirement_index}/{requirement_count}: {requirement_id} (Chapter: {chapter_index}/{chapter_count} Section: {section_index}/{section_count})")

                section_file.write(f"### {requirement_id}  \n  \n")
                section_file.write(f"Ref: {requirement_code}  \n")

                if requirement['L3']['Required']:
                    requirement_level = "3"
                    requirements_description = requirement['L3']['Requirement']
                elif requirement['L2']['Required']:
                    requirement_level = "2"
                    requirements_description = requirement['L2']['Requirement']
                elif requirement['L1']['Required']:
                    requirement_level = "1"
                    requirements_description = requirement['L1']['Requirement']
                else:
                    requirement_level = "0"
                    requirements_description = "[optional depending on context]"

                section_file.write(f"ASV Level: {requirement_level} \n  \n")

                if requirements_description:
                    section_file.write(f"ASV Requirement: {requirements_description} \n  \n")

                # TODO:: link to relevant CWE or NIST references

                section_file.write(f"{requirement_description}  \n  \n")

                request_steps = f"Produce a step-by-step guide to test the OWASP ASVS requirement: {requirement_id} ({requirement_code})."
                request_steps += f"\nThe Requirement is from Chapter: \"{chapter_name}\", Section: \"{section_name}\"."
                request_steps += f"\nRequirement details: \"{requirement_description}\"."
                request_steps += f"\nApplication Security Verification (ASV) Level: {requirement_level}."
                
                if requirements_description:
                    request_steps += " ASV Requirement: {requirements_description}."

                request_steps += "\nIf relevant, assume a modern web application and infer that it should be using modern best practice."
                request_steps += "\nIf you can, make the example technology agnostic; if you cannot, then assume a {default_tech_stack}."
                request_steps += "\nContent is to be included directly into a markdown file (under a third-level heading for this requirement)"
                request_steps += "; so do not include additional description of what you're producing, or platitudes etc. in your response."
                request_steps += "\nBreak down the content as needed using appropriate markdown headers etc."

                print(f"Chapter {chapter_index}/{chapter_count} Section {section_index}/{section_count} Req {requirement_index}/{requirement_count}: Generating Steps")
                requirement_messages.append({"role": "user", "content": request_steps})
                requirement_steps_response = openai.ChatCompletion.create(
                                model=model_id,
                                messages=requirement_messages
                            )

                requirement_steps = requirement_steps_response['choices'][0]['message']['content'] # type: ignore
                requirement_messages.append({"role": "assistant", "content": requirement_steps})

                if section_intro.startswith("I'm sorry, but as an AI language model"):
                    print(f"ERROR: Requirement: {requirement_code} Steps: {requirement_steps}")
                    requirement_steps = "OPENAI_ERROR_INVALID_RESPONSE"
                else:
                    section_file.write(f"\n#### *Steps to Verify Requirement:*  \n  \n")
                    section_file.write(f"\n{requirement_steps}  \n  \n")

                
            section_file.close()

        chapter_readme.close()

    readme.close()

def main():
    if not sys.stdin.isatty():
        exit(1)

    load_dotenv()

    openai.api_key = config.get("api_key", os.getenv("OPENAI_KEY"))
    openai.organization = config.get("org_id", os.getenv("OPENAI_ORG"))

    model_id = config.get("model_id", os.getenv("OPENAI_MODEL"))
    validate_openai_config(model_id)

    output_dir = "/home/vscode"
    repo_name = "owasp-asvs-testing-guide"
    folder_name = "testing-guide"

    username = get_logged_in_username()
    requirements = fetch_asvs_requirements()
    create_repo(output_dir, username, repo_name, False)
    create_directory_structure_and_files(os.path.join(output_dir, repo_name), requirements, folder_name)

if __name__ == "__main__":
    main()