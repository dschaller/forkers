import argparse
import json
import os
import shutil

import requests

MEMBERS_URL = 'https://api.github.com/orgs/{}/members'
REPOS_URL = 'https://api.github.com/orgs/{}/repos?type=private'
FORKS_URL = 'https://api.github.com/repos/{}/forks'

FOUND_MESSAGE = 'Found {} {} for the {} organization'
FOUND_IN_CACHE_MESSAGE = '{} (Cached)'.format(FOUND_MESSAGE)


def find_forked_repos(**kwargs):
    if kwargs.get('clearcache'):
        _clear_cache()

    organization = kwargs.get('organization')
    github_repos, repos_cached = organization_repos(organization)
    message = FOUND_IN_CACHE_MESSAGE if repos_cached else FOUND_MESSAGE
    print(message.format(len(github_repos), 'repos', organization))

    org_members, org_members_cached = organization_members(organization)
    message = FOUND_IN_CACHE_MESSAGE if org_members_cached else FOUND_MESSAGE
    print(message.format(len(org_members), 'members', organization))

    for repo_name in github_repos:
        forks, forks_cached = forked_repos(repo_name, organization)
        if len(forks) == 0:
            continue
        print(
            'Found {} forks of repo: {}{}'.format(
                len(forks),
                repo_name,
                ' (Cached)' if forks_cached else ''
            )
        )
        if not kwargs.get('shield'):
            print('    Forkers:')
            for fork in forks:
                print('        - {}'.format(fork.get('owner')))
                fork_collaborators = fetch_fork_collaborators(
                    fork,
                    organization
                )
                determine_foreign_collaborators(
                    fork_collaborators,
                    org_members,
                    organization
                )


def organization_repos(organization):
    CACHE_NAME = '{}/organization_repos'.format(organization)
    cached_data = _cached_data(CACHE_NAME)
    if cached_data:
        return cached_data, True

    repos = get(REPOS_URL.format(organization))
    organization_repos = [repo.get('full_name') for repo in repos]
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


def forked_repos(repo_name, organization):
    CACHE_NAME = '{}/repos/{}'.format(organization, repo_name)
    cached_data = _cached_data(CACHE_NAME)
    if cached_data is not None:
        return cached_data, True

    forks = []
    all_forks = get(FORKS_URL.format(repo_name))
    for fork in all_forks:
        forks.append({
            'name': repo_name,
            'owner': fork.get('owner', {}).get('login'),
            'collabortors_url': fork.get(
                'collaborators_url'
            ).rstrip('{/collaborator}')
        })
    _cache_data(CACHE_NAME, forks)
    return forks, False


def fetch_fork_collaborators(fork, organization):
    # CACHE_NAME = '{}/fork_collaborators/{}'.format(
    #     organization,
    #     fork.get('name')
    # )
    # cached_data = _cached_data(CACHE_NAME)
    # if cached_data:
    #     print('            Using cached collaborators for {}'.format(
    #        fork.get('name'))
    #    )
    #     return cached_data

    try:
        collaborators = get(fork.get('collabortors_url'))
    except Exception as e:
        print ('            {}'.format(e))
        collaborators = []
    collaborators = [
        collaborator.get('login') for collaborator in collaborators
    ]
    # _cache_data(CACHE_NAME, collaborators)
    return collaborators


def determine_foreign_collaborators(fork_collaborators, org_members, org):
    illegal_collaborators = []

    for collaborator in fork_collaborators:
        if collaborator not in org_members:
            illegal_collaborators.append(collaborator)

    if illegal_collaborators:
        print('            - Potential security vulnerability: found {} collaborators not in the {} organization.'.format(len(illegal_collaborators), org))
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
    parser = argparse.ArgumentParser(description='Audit GitHub forks')
    parser.add_argument('--clearcache', '-cc', default=False,
                        action='store_true',
                        help='Clear all of the cached data.')
    # TODO: Implement additional caching logic
    # parser.add_argument('--clearcacheorg', '-cco',
    #                    default=defaut_organization, type=str,
    #                     help='Clear all cached data for an organization.')
    # parser.add_argument('--clearcacherepos', '-ccr', default=False,
    #                    action='store_true',
    #                     help='Clear cached repo data.')
    # parser.add_argument('--clearcachemembers', '-ccm', default=False,
    #                    action='store_true',
    #                     help='Clear cached members data.')
    # parser.add_argument('--clearcacheforks', '-ccf', default=False,
    #                    action='store_true',
    #                     help='Clear cached fork data.')
    # parser.add_argument('--clearcacheforkcollab', '-ccfc', default=False,
    #                    action='store_true',
    #                     help='Clear cached fork collaborators data.')
    parser.add_argument('--organization', '-o', default=defaut_organization,
                        type=str, help='The GitHub organization to audit.')
    parser.add_argument('--shield', '-s', default=False, action='store_true',
                        help='The GitHub organization to audit.')

    args = parser.parse_args()
    find_forked_repos(**vars(args))
