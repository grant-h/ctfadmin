import sys
import os
import re
import logging
import github

from repo import *
from walk import create_git_tree
import customargs

try:
    from IPython import embed
except ImportError:
    def embed():
        pass

log = logging.getLogger(__name__)

cmd_create_parser = customargs.ArgumentParser(prog='create')
cmd_create_parser.add_argument('--type',
        help="What category type to create",
        required=True
)
cmd_create_parser.add_argument('--user',
        help="The GitHub user to associate the challenge with",
        required=True
)

def validate_category(config, category):
    for cat in config.categories:
        if category == cat["short_name"] or category == cat["full_name"]:
            return cat

    return None

def fetch_user(gh, username):
    try:
        user_object = gh.get_user(username)
    except github.UnknownObjectException:
        log.error('Unknown GitHub user @%s', username)
        return None

    return user_object

def cmd_create(config, gh, org, args):
    username = args.user
    ctfname = config.ctfname
    category = validate_category(config, args.type)

    if category is None:
        log.error("Category '%s' not valid for the CTF", args.type)
        return

    category_fn = category["full_name"]
    repo_name = config.prefix + category["short_name"]

    # Lookup the manager user by username
    user_object = fetch_user(gh, username)

    if user_object is None:
        return

    full_name = user_object.name

    # Fetch all the challenge repos to determine the next numbered one to create
    repos = get_challenge_repos(config, org)

    maxnumber = 0
    for r in repos:
        if r.name.startswith(repo_name):
            try:
                num = int(r.name[len(repo_name):])

                if num > maxnumber:
                    maxnumber = num
            except ValueError:
                log.error("Invalid challenge repository name format '%s'. Expected number at end", r.name)
                return

    # Create the next numbered challenge
    maxnumber += 1
    repo_name = repo_name + str(maxnumber)
    desc = """{ctfname} {category_fn} challenge. Assigned to {full_name} (@{username}).""".format(**locals())

    # Get all the organization teams to find the admin one (if any)
    teams = org.get_teams()

    ctf_admin_team = None

    # if an admin team was specified, make sure to include it
    if len(config.admin_team) > 0:
        for t in teams:
            if t.name == config.admin_team:
                ctf_admin_team = t
                break

        if ctf_admin_team is None:
            log.error("Unable to find the admin team name '%s'",
                    config.admin_team)
            return

    if len(repos):
        new_repo = repos[0]
        log.info("Going with repo %s", new_repo.name)
    else:
        # Create the new repo
        # TODO: make sure admin team actually has admin (it has read by default)
        new_repo = create_repo(org, repo_name, user_object,
                desc, admin_user=ctf_admin_team)

    if new_repo is None:
        return

    try:
        head = new_repo.get_git_ref('heads/master')
        base_tree = new_repo.get_git_tree(head.object.sha)
        base_commit = new_repo.get_git_commit(head.object.sha)
        log.info('Retrieved base commit on the master branch')
    except github.GithubException as e:
        log.error('Unable to retrieve base commit, tree, or reference')
        log.error('Reason: %s', str(e))
        log.error("Rolling back created repo...")

        delete_repo(new_repo)
        return None

    new_tree = create_git_tree(new_repo, config.template_dir)

    if new_tree is None:
        return None

    try:
        new_commit = new_repo.create_git_commit('Added initial CTF template', new_tree, [base_commit])
        head.edit(new_commit.sha)
    except github.GithubException as e:
        log.error("Failed to create commit object")
        log.error("Reason: %s", e)

    log.info("Repository loaded with template files from '%s'", config.template_dir)

    return

cmd_list_parser = customargs.ArgumentParser(prog='list')
cmd_list_parser.add_argument('--type', help="What category type to list")

def cmd_list(config, gh, org, args):
    repos = get_challenge_repos(config, org)

    for r in repos:
        match = re.match(config.prefix + r'([a-zA-Z]+)([0-9]+)', r.name)

        if not match:
            log.warning("Malformed CTF challenge repo name '%s'", r.name)
            continue

        print("%s - category:%s #%d" %(r.name, match.group(1), int(match.group(2))))

cmd_delete_parser = customargs.ArgumentParser(prog='delete')
cmd_delete_parser.add_argument('name', help="Which repository to delete")

def cmd_delete(config, gh, org, args):
    repos = get_challenge_repos(config, org)

    for r in repos:
        if r.name == args.name:
            delete_repo(r)
            return

    log.error("Unable to find the repository '%s'", args.name)
