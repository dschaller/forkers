# Forkers
[![Build Status](https://travis-ci.com/dschaller/forkers.svg?token=S1PppF2H8FVrQHs8pw3M&branch=master)](https://travis-ci.com/dschaller/forkers)

A script that:
  - finds and reports users who have forked an organizations repos
  - compares the collaborators of the forks with the organization members to determine if anyone not in the organization has been added
  

## Usage
In order to run the script you must have an environment variable set with a GitHub token that can access the organization you wish to audit. It can be set by running the following command before running the scripts.
```bash
export GITHUB_TOKEN=1234567890
```

You should now be able to run:
```bash
python fork_audit.py -o {organization_name}
```

In order to allow for the script to be run multiple times, back to back, there is a layer of caching to avoid hitting GitHub's ratelimiting.
All cached files will be put into `cache/{organization}`.
To clear the cache before running run the script with either `--clearcache` or `-cc`.
