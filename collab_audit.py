import argparse
import json
import os
import shutil

import requests

MEMBERS_URL = 'https://api.github.com/orgs/{}/members'
REPOS_URL = 'https://api.github.com/orgs/{}/repos?type=private'

FOUND_MESSAGE = 'Found {} {} for the {} organization'
FOUND_IN_CACHE_MESSAGE = '{} (Cached)'.format(FOUND_MESSAGE)


def find_questionable_collaborators(**kwargs):
    if kwargs.get('clearcache'):
        _clear_cache()

    organization = kwargs.get('organization')
    github_repos, repos_cached = organization_repos(organization)
    message = FOUND_IN_CACHE_MESSAGE if repos_cached else FOUND_MESSAGE
    print(message.format(len(github_repos), 'repos', organization))

    org_members, org_members_cached = organization_members(organization)
    message = FOUND_IN_CACHE_MESSAGE if org_members_cached else FOUND_MESSAGE
    print(message.format(len(org_members), 'members', organization))

    for repo in github_repos:
        print('        - {}'.format(repo.get('name')))
        collaborators = fetch_collaborators(
            repo,
            organization
        )
        determine_foreign_collaborators(
            collaborators,
            org_members,
            organization
        )


def organization_repos(organization):
    CACHE_NAME = '{}/organization_repos'.format(organization)
    cached_data = _cached_data(CACHE_NAME)
    if cached_data:
        return cached_data, True

    repos = get(REPOS_URL.format(organization))
    organization_repos = []
    for repo in repos:
        organization_repos.append({
            'name': repo.get('full_name'),
            'collaborators_url': repo.get('collaborators_url').rstrip('{/collaborator}')
        })
    _cache_data(CACHE_NAME, organization_repos)
    return organization_repos, False


def organization_members(organization):
    CACHE_NAME = '{}/organization_members'.format(organization)
    cached_data = _cached_data(CACHE_NAME)
    if cached_data:
        return cached_data, True

    members = get(MEMBERS_URL.format(organization))
    organization_members = [member.get('login') for member in members]
    _cache_data(CACHE_NAME, organization_members)
    return organization_members, False


def fetch_collaborators(repo, organization):
    CACHE_NAME = '{}/collaborators/{}'.format(
        organization,
        repo.get('name')
    )
    cached_data = _cached_data(CACHE_NAME)
    if cached_data:
        print('            Using cached collaborators for {}'.format(
           repo.get('name'))
       )
        return cached_data

    collaborators = []
    try:
        collab_url = repo.get(u'collaborators_url')
        collaborators = get(collab_url)
    except Exception as e:
        print ('            {}'.format(e))
        collaborators = []
    collaborators = [
        collaborator.get('login') for collaborator in collaborators
    ]
    _cache_data(CACHE_NAME, collaborators)
    return collaborators


def determine_foreign_collaborators(collaborators, org_members, org):
    illegal_collaborators = []

    for collaborator in collaborators:
        if collaborator not in org_members:
            illegal_collaborators.append(collaborator)

    if illegal_collaborators:
        print('            - Potential security vulnerability: found {} collaborators not in the {} organization.'.format(len(illegal_collaborators), org))  # noqa
    for illegal_collaborator in illegal_collaborators:
        print('                - {}'.format(illegal_collaborator))


def _cached_data(filename):
    filename = 'cache/{}.txt'.format(filename)
    try:
        with open(filename, 'r+') as f:
            contents = f.read()
            if contents:
                return json.loads(contents)
    except IOError:
        pass


def _cache_data(filename, data):
    filename = 'cache/{}.txt'.format(filename)
    try:
        os.makedirs(filename[:filename.index(filename.split('/')[-1])])
    except OSError as e:
        if e.errno != 17:
            print('Could not create cache for: {}'.format(filename))

    with open(filename, 'w+') as f:
        f.write(json.dumps(data))


def _clear_cache():
    try:
        shutil.rmtree('cache')
    except OSError:
        pass


def get(url, pagenate=True):
    github_session = _github_session()
    response_data = []
    if not pagenate:
        response = github_session.get(url)
        text = response.text
        if response.status_code != 200:
            print('Encountered error during GET request: {}'.format(
                response.text
            ))
            text = {}
        return json.loads(text)
    for x in xrange(10000):
        if '?' not in url:
            paged_url = '{}?page={}'.format(url, x+1)
        else:
            paged_url = '{}&page={}'.format(url, x+1)
        response = github_session.get(paged_url)
        paged_response = json.loads(response.text)
        if not paged_response or response.status_code != 200:
            if response.status_code != 200:
                raise Exception(
                    'Encountered error during GET request to {} : {}'.format(
                        paged_url,
                        response.text
                    )
                )
            break
        response_data.extend(paged_response)
    return response_data


def _github_session():
    """Generates a session with valid headers for GitHub."""
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        raise EnvironmentError('GITHUB_TOKEN missing from environment')

    session = requests.Session()
    session.headers.update({
        'Authorization': 'token {}'.format(github_token),
        'Accept': 'application/vnd.github.v3+json'
    })
    return session


if __name__ == '__main__':
    defaut_organization = os.environ.get('ORGANIZATION')
    parser = argparse.ArgumentParser(description='Audit GitHub collaborators')
    parser.add_argument('--clearcache', '-cc', default=False,
                        action='store_true',
                        help='Clear all of the cached data.')
    parser.add_argument('--organization', '-o', default=defaut_organization,
                        type=str, help='The GitHub organization to audit.')
    parser.add_argument('--shield', '-s', default=False, action='store_true',
                        help='The GitHub organization to audit.')

    args = parser.parse_args()
    if not args.organization:
        raise RuntimeError('Organization required to run script.')
    find_questionable_collaborators(**vars(args))
