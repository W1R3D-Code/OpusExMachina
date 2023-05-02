import json
import os
import requests
import subprocess
import requests
import re

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

    for requirement in requirements["Requirements"]:
        chapter_code = f"{name}V{version}-{requirement['Ordinal']}"
        chapter_shortCode = requirement['Shortcode']
        chapter_shortName = requirement["ShortName"]

        chapter_name = f"{chapter_shortCode} {chapter_shortName}"
        chapter_file_name = chapter_name.replace(" ", "_")

        chapter_dir = os.path.join(out_dir, chapter_file_name)

        if not os.path.exists(chapter_dir):
            os.makedirs(chapter_dir)

        readme.write(f"- [{chapter_name}](./{chapter_file_name}/README.md)\n")

        chapter_readme = open(os.path.join(chapter_dir, "README.md"), "w")
        chapter_readme.write(f"# {chapter_name}\n  \n")
        chapter_readme.write("## Sections\n  \n")

        for section in requirement["Items"]:
            section_code = f"{chapter_code}.{section['Shortcode'][1:]}"
            section_name = f"{chapter_shortCode}.{section['Shortcode'][1:]} {section['Name']}"
            section_file_name = section_name.replace(" ", "_")
            
            chapter_readme.write(f"- [{section_name}](./{section_file_name}.md)\n")

            section_file = open(os.path.join(chapter_dir, f"{section_file_name}.md"), "w")

            # TODO:: Add meta-data via markdown comments incl. ASVS version & req number, and agregated L1/2/3 required status + CWE & NIST references

            section_file.write(f"# {section_name}\n")

            section_file.write("\n<!-- Introductory text, prerequisites, and tool usage instructions -->  \n  \n")

            section_file.write("## Requirements\n  \n")
            
            for req in section["Items"]:
                req_id = req['Shortcode']
                req_code = f"{section_code}.{req_id[1:]}"
                req_description = req['Description']

                section_file.write(f"### {req_id}  \n  \n")

                section_file.write(f"Ref: {req_code}  \n")

                requirement_levels = []
                requirements_description = ""
                if req['L1']['Required']:
                    requirement_levels.append("L1")
                    requirement_desc = req['L1']['Requirement'] if req['L1']['Requirement'] else "True"
                    requirements_description += f"L1: {requirement_desc}  \n"

                if req['L2']['Required']:
                    requirement_levels.append("L2")
                    requirement_desc = req['L2']['Requirement'] if req['L2']['Requirement'] else "True"
                    requirements_description += f"L2: {requirement_desc}  \n"

                if req['L3']['Required']:
                    requirement_levels.append("L3")
                    requirement_desc = req['L3']['Requirement'] if req['L3']['Requirement'] else "True"
                    requirements_description += f"L3: {requirement_desc}  \n"

                if len(requirement_levels) > 0:
                    section_file.write(f"Required level{'s' if len(requirement_levels) > 1 else ''}: {', '.join(requirement_levels)}  \n  \n")
                    section_file.write("#### *Requirements:*  \n  \n")
                    section_file.write(f"{requirements_description}  \n  ")

                else:
                    section_file.write(f"Required level: L0 [optional depending on context]  \n")

                # TODO:: link to relevant CWE or NIST references

                section_file.write(f"{req_description}  \n  \n")

                section_file.write("\n<!-- Task steps, and expected results -->  \n  \n")
            section_file.close()

        chapter_readme.close()

    readme.close()

def main():
    output_dir = "/home/vscode"
    username = get_logged_in_username()
    repo_name = "owasp-asvs-testing-guide"
    requirements = fetch_asvs_requirements()
    create_repo(output_dir, username, repo_name, False)
    create_directory_structure_and_files(os.path.join(output_dir, repo_name), requirements, "testing-guide")

if __name__ == "__main__":
    main()