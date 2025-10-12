#!/usr/bin/env python3
"""
Automate creation of a GitHub Project V2 board, labels, and roadmap issues.
Reads credentials and repository from environment variables to avoid embedding secrets in code.
Requires:
  - GITHUB_TOKEN env var with a personal access token
  - GITHUB_REPOSITORY env var in "owner/repo" format
"""
import os
import sys
import requests

# Load credentials from environment
TOKEN = os.getenv('GITHUB_TOKEN')
REPO_NAME = os.getenv('GITHUB_REPOSITORY')  # format: owner/repo
if not TOKEN or not REPO_NAME:
    sys.exit('Error: Set GITHUB_TOKEN and GITHUB_REPOSITORY (owner/repo)')
try:
    OWNER, REPO = REPO_NAME.split('/', 1)
except ValueError:
    sys.exit("Error: GITHUB_REPOSITORY must be 'owner/repo'")

# GitHub endpoints
REST_API = 'https://api.github.com'
GRAPHQL_API = 'https://api.github.com/graphql'

def graphql_request(query, variables=None):
    headers = {
        'Authorization': f'bearer {TOKEN}',
        'Content-Type': 'application/json'
    }
    payload = {'query': query, 'variables': variables or {}}
    try:
        r = requests.post(GRAPHQL_API, headers=headers, json=payload)
    except requests.RequestException as e:
        sys.exit(f'Network error: {e}')
    if r.status_code != 200:
        sys.exit(f'GraphQL HTTP {r.status_code}: {r.text}')
    data = r.json()
    if 'errors' in data:
        sys.exit(f'GraphQL errors: {data["errors"]}')
    return data.get('data')

def main():
    # 1) Get repository ID via GraphQL
    query_repo = '''
    query($owner:String!,$name:String!){
      repository(owner:$owner,name:$name){id}
    }
    '''
    data = graphql_request(query_repo, {'owner': OWNER, 'name': REPO})
    repo_id = data['repository']['id']
    print(f'Repository ID: {repo_id}')

    # 2) Create a new Project V2
    proj_name = 'LLM Firewall Roadmap'
    proj_body = 'Kanban board for the prompt injection defense roadmap'
    mut_proj = '''
    mutation($ownerId:ID!,$title:String!,$shortDescription:String!){
      createProjectV2(input:{ownerId:$ownerId,title:$title,shortDescription:$shortDescription}){
        projectV2 { id }
      }
    }
    '''
    created = graphql_request(mut_proj, {'ownerId': repo_id, 'title': proj_name, 'shortDescription': proj_body})
    project_id = created['createProjectV2']['projectV2']['id']
    print(f'Created Project V2 ID: {project_id}')

    # 3) Create columns
    columns = {}
    col_names = ['Backlog', 'To Do', 'In Progress', 'Review', 'Done']
    mut_col = '''
    mutation($projId:ID!,$name:String!){
      addProjectV2Column(input:{projectId:$projId,name:$name}){
        column{id name}
      }
    }
    '''
    for name in col_names:
        out = graphql_request(mut_col, {'projId': project_id, 'name': name})
        col = out['addProjectV2Column']['column']
        columns[name] = col['id']
        print(f"Created column '{col['name']}' (ID {col['id']})")

    # 4) Create labels via REST
    rest_headers = {'Authorization': f'token {TOKEN}', 'Accept': 'application/vnd.github.v3+json'}
    labels = {
        'roadmap-step-1': 'ededed',
        'type:feature': '0e8a16',
        'type:test': 'c5def5',
        'security': 'f9d0c4',
    }
    for lname, color in labels.items():
        payload = {'name': lname, 'color': color}
        r = requests.post(f'{REST_API}/repos/{OWNER}/{REPO}/labels', headers=rest_headers, json=payload)
        if r.status_code == 201:
            print(f"Created label '{lname}'")
        else:
            print(f"Label '{lname}' exists or cannot be created ({r.status_code})")

    # 5) Create roadmap issues and add to project
    epics = [
        {
            'title': 'Step 1: Minimal Prototype – Action-Selector',
            'body': 'Implement orchestrator and executor for basic add/multiply agent.',
            'labels': ['roadmap-step-1', 'type:feature'],
        },
        {
            'title': 'Step 1.1: Harden Orchestrator JSON-Plan Validation',
            'body': 'Validate orchestrator output keys: action and args[a,b].',
            'labels': ['roadmap-step-1', 'security'],
        },
        {
            'title': 'Step 1.2: Harden Executor Args Validation',
            'body': 'Validate executor args object contains only a and b.',
            'labels': ['roadmap-step-1', 'security'],
        },
    ]
    for epic in epics:
        r = requests.post(f'{REST_API}/repos/{OWNER}/{REPO}/issues', headers=rest_headers, json=epic)
        if r.status_code not in (200, 201):
            print(f"Failed to create issue '{epic['title']}': HTTP {r.status_code}")
            continue
        issue = r.json()
        node_id = issue['node_id']
        number = issue['number']
        print(f"Created issue #{number}: {epic['title']}")
        # add to project
        mut_item = '''
        mutation($projId:ID!,$contentId:ID!){
          addProjectV2Item(input:{projectId:$projId,contentId:$contentId}){
            item{id}
          }
        }
        '''
        graphql_request(mut_item, {'projId': project_id, 'contentId': node_id})
        print(f"Added issue #{number} to project")

    print('Setup complete.')

if __name__ == '__main__':
    main()