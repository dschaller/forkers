# Forkers

A script that:
  - finds and reports users who have forked an organizations repos
  - compares the collaborators of the forks with the organization members to determine if anyone not in the organization has been added
  

## Usage
```bash
python fork_audit.py -o {organization_name}
```

In order to allow for the script to be run multiple times, back to back, there is a layer of caching to avoid hitting GitHub's ratelimiting.
All cached files will be put into `cache/{organization}`.
To clear the cache before running run the script with either `--clearcache` or `-cc`.
