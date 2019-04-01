import sys
import os
import re
import logging
import github
import argparse

from repo import *
from walk import create_git_tree

log = logging.getLogger(__name__)

INITIAL_COMMIT_NUM = 2

class ArgumentParser(argparse.ArgumentParser):
    def exit(self, status=0, message=None):
        raise IOError(message)
        pass

cmd_create_parser = ArgumentParser(prog='create')
cmd_create_parser.add_argument('--type',
        help="What category type to create",
        required=True
)
cmd_create_parser.add_argument('--user',
        help="The GitHub user to associate the challenge with",
        required=True
)

def fetch_user(gh, username):
    try:
        user_object = gh.get_user(username)
    except github.UnknownObjectException:
        log.error('Unknown GitHub user @%s', username)
        return None

    return user_object

def get_admin_team(config, org):
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

    return ctf_admin_team

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
    full_name = user_object.name

    if full_name:
        desc = """{ctfname} {category_fn} challenge. Assigned to {full_name} (@{username}).""".format(**locals())
    else:
        desc = """{ctfname} {category_fn} challenge. Assigned to @{username}.""".format(**locals())

    # Get the admin team (if any)
    ctf_admin_team = get_admin_team(config, org)

    # Create the new repo
    new_repo = create_repo(org, repo_name, user_object,
            desc, admin_user=ctf_admin_team)

    if new_repo is None:
        return

    if ctf_admin_team:
        try:
            ctf_admin_team.set_repo_permission(new_repo, 'admin')
        except github.GithubException as e:
            log.warning("Failed to set the repository permissions to admin for team '%s'",
                    str(t))
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

    variables = {
            'CHALLENGE_CATEGORY_FULL' : category["full_name"],
            'CHALLENGE_CATEGORY_SHORT' : category["short_name"],
            'CTF_NAME' : config.ctfname,
            # Feel free to extend this to meet your needs
    }

    # add the base template directory to each variable file entry
    variable_files = map(lambda x: os.path.join(config.template_dir, x), config.variable)

    def read_hook(path):
        try:
            with open(path, 'rb') as fp:
                contents = fp.read()

                if path in variable_files:
                    # do some error checking just incase you mistype
                    found_variables = re.findall(r'%[-A-Za-z_0-9]+%', contents)
                    for var in found_variables:
                        if var[1:len(var)-1] not in variables:
                            log.warning("Unknown variable '%s' in file '%s'",
                                    var, path)

                    for var,repl in variables.iteritems():
                        contents = contents.replace("%"+var+"%", repl)

                return contents
        except IOError:
            log.error("Unable to open file '%s' for reading", path)
            return None

    # Load all of the files into a tree structure (contents and all)
    new_tree = create_git_tree(new_repo, config.template_dir, file_read_hook=read_hook)

    if new_tree is None:
        return None

    try:
        new_commit = new_repo.create_git_commit('Added initial CTF template', new_tree, [base_commit])
        head.edit(new_commit.sha)
    except github.GithubException as e:
        log.error("Failed to create commit object")
        log.error("Reason: %s", e)
        # TODO: delete trees and blobs
        return

    log.info("Repository loaded with template files from '%s'", config.template_dir)
    log.info("Repository ready: %s", new_repo.html_url)

    return

cmd_list_parser = ArgumentParser(prog='list')
cmd_list_parser.add_argument('--type', help="What category type to list")
cmd_list_parser.add_argument('--details', help="Show extra repository details",
        action="store_true")

def cmd_list(config, gh, org, args):
    repos = get_challenge_repos(config, org)
    target_category = None

    if args.type:
        target_category = validate_category(config, args.type)

        if target_category is None:
            log.error("Category '%s' not valid for the CTF", args.type)
            return

    for r in repos:
        name = r.name
        category = r.category
        info = "%s - \"%s\"" % (name, r.description)
        extra = ""

        if target_category and target_category["short_name"] != category:
            continue

        if args.details:
            total_commits = r.get_commits().totalCount
            #contributors = []

            #for c in r.get_contributors():
            #    contributors += [c]

            #contributors = ",".join(map(lambda x: x.login, contributors))
            extra = " commits=%d" % (total_commits)

        print("%s%s" % (info, extra))

cmd_delete_parser = ArgumentParser(prog='delete')
cmd_delete_parser.add_argument('name', help="Which repository to delete")
cmd_delete_parser.add_argument('--force', help="Forces the deletion of repositories with more than the default commit count", action="store_true")

def cmd_delete(config, gh, org, args):
    repos = get_challenge_repos(config, org)

    for r in repos:
        if r.name == args.name:
            total_commits = r.get_commits().totalCount

            # the repository has been modified
            if total_commits > INITIAL_COMMIT_NUM and not args.force:
                log.warning("Refusing to delete repository with more commits than the default")
                log.warning("Specify the --force flag to confirm the deletion")
                return

            delete_repo(r)
            return

    log.error("Unable to find the repository '%s'", args.name)

cmd_stats_parser = ArgumentParser(prog='stats')
cmd_stats_parser.add_argument('report_type', choices=["progress"],
        help="What report should be generated")

def cmd_stats(config, gh, org, args):
    repos = get_challenge_repos(config, org)

    report = args.report_type

    repo_stats = []

    log.info("Collecting metadata from %d repos...", len(repos))

    for r in repos:
        stat = {}
        stat["repo"] = r
        stat["name"] = r.name
        stat["author"] = re.search(r'@([a-zA-Z0-9]+)', r.description).group(1).lower()
        stat["commits"] = r.get_commits().totalCount
        stat["category"] = r.category
        stat["num"] = r.chal_num
        repo_stats += [stat]

    output = ""

    if report == "progress":
        started = list(filter(lambda x: x["commits"] > INITIAL_COMMIT_NUM, repo_stats))
        not_started = list(filter(lambda x: x["commits"] <= INITIAL_COMMIT_NUM, repo_stats))

        output += "[%s Challenge Progress]\n" % (config.ctfname)

        repo_breakdown = {}
        started_repo_breakdown = {}
        not_started_repo_by_author = {}

        for st in repo_stats:
            repo_breakdown[st["category"]] = repo_breakdown.get(st["category"], 0) + 1
        for st in started:
            started_repo_breakdown[st["category"]] = started_repo_breakdown.get(st["category"], 0) + 1
        for st in not_started:
            not_started_repo_by_author[st["author"]] = not_started_repo_by_author.get(st["author"], []) + [st]

        repo_category_freq = sorted(repo_breakdown.items(), key=lambda x: x[0])
        repo_breakdown_str = ["%d %s" % (n, c) for c, n in repo_category_freq]
        repo_breakdown_str = "(%s)" % ", ".join(repo_breakdown_str)

        started_repo_breakdown_str = ["%d/%d %s" % (started_repo_breakdown.get(c, 0), n, c) for c, n in repo_category_freq]
        started_repo_breakdown_str = "(%s)" % ", ".join(started_repo_breakdown_str)

        output += "Allocated challenges: %d %s\n" % (len(repos), repo_breakdown_str)
        output += "Started challenges (by commits): %d/%d %s\n" % (len(started), len(repos), started_repo_breakdown_str)

        output += "User Reminders:\n"

        for user, user_repos in sorted(not_started_repo_by_author.items(), key=lambda x: x[0]):
            missing = len(user_repos)
            repo_names = sorted(list(map(lambda x: x["name"], user_repos)))
            report_line = ""
            from datetime import datetime
            today = str(datetime.today())

            if missing > 1:
                chal_pl = "challenges"
                missing_line = "assigned challenges *[%s]* have" % (", ".join(repo_names[:-1]) + " and " + repo_names[-1])
            else:
                chal_pl = "challenge"
                missing_line = "assigned challenge *[%s]* has" % (repo_names[0])

            output += "Hi %s, this is a semi-automated message informing you that your %s zero commits as of today.\n" % (user, missing_line)
            output += "Please commit what you have, regardless if it is complete ASAP, or declare your %s as Will Not Write (WNR).\n\n" % (chal_pl)

    print(output)

cmd_coalesce_parser = ArgumentParser(prog='coalesce')

def cmd_coalesce(config, gh, org, args):
    repos = get_challenge_repos(config, org)

    if len(repos) == 0:
        log.error("No repos to coalesce")
        return

    master_repo_name = config.prefix + "challenges"
    description = "%s master challenge repository." % config.ctfname

    # Case 1: Brand new master repo
    #   1. Create repo
    #   2. Build up .gitmodules blob
    #   3. Build git trees, one per category
    #   4. Insert submodule blobs into their respective category trees
    #   5. Create new commit!
    # Case 2: Updating master repo
    #   TODO

    # Get the admin team (if any)
    ctf_admin_team = get_admin_team(config, org)

    # Create the new repo
    new_repo = create_repo(org, master_repo_name, description, admin_user=ctf_admin_team)

    if new_repo is None:
        return

    if ctf_admin_team:
        try:
            ctf_admin_team.set_repo_permission(new_repo, 'admin')
        except github.GithubException as e:
            log.warning("Failed to set the repository permissions to admin for team '%s'",
                    str(t))
    try:
        head = new_repo.get_git_ref('heads/master')
        base_tree = new_repo.get_git_tree(head.object.sha)
        base_commit = new_repo.get_git_commit(head.object.sha)
        log.info('Retrieved base commit for %s', master_repo_name)
    except github.GithubException as e:
        log.error('Unable to retrieve base commit, tree, or reference')
        log.error('Reason: %s', str(e))
        log.error("Rolling back created repo...")

        delete_repo(new_repo)
        return None

    master_repo = None
    by_category = {}

    for repo in repos:
        cat = repo.category
        if cat not in by_category:
            by_category[cat] = []

        by_category[cat] += [repo]

    tl_elements = []
    submodules = []

    for cat, repo_list in sorted(by_category.items()):
        elements = []
        for r in repo_list:
            repo_name = '%s%d' % (cat, r.chal_num)
            path = '%s/%s' % (cat, repo_name)
            branch = 'master'
            url = r.ssh_url

            try:
                r_head = r.get_git_ref('heads/%s' % branch)
                r_base_tree = r.get_git_tree(r_head.object.sha)
                r_base_commit = r.get_git_commit(r_head.object.sha)
                log.info('Retrieved base commit for %s on the %s branch', r.name, branch)
            except github.GithubException as e:
                log.error('Unable to retrieve base commit, tree, or reference')
                log.error('Reason: %s', str(e))
                log.error("Rolling back created repo...")

                delete_repo(new_repo)
                return None

            commit = r_head.object.sha

            submodule = GitSubmodule(path, url, branch, commit)
            submodules += [submodule]

            elements += [github.InputGitTreeElement(repo_name, object_types["submodule"],
                'commit', sha=commit)]

        # Create the directory for this category
        # Store sha for later reference
        try:
            new_tree = new_repo.create_git_tree(elements)
        except github.GithubException as e:
            log.error("Failed to create a git tree object for category '%s'", cat)
            log.error("Reason: %s", e)
            log.error("Rolling back created repo...")

            delete_repo(new_repo)
            return None

        tl_elements += [github.InputGitTreeElement(cat, object_types["directory"], 'tree', sha=new_tree.sha)]

    # Emit .gitmodules blob
    gitmodules_content = "".join([str(x) for x in submodules])
    tl_elements += [github.InputGitTreeElement(".gitmodules", object_types["file"],
        'blob', content=gitmodules_content)]

    # Create top level tree
    try:
        tl_tree = new_repo.create_git_tree(tl_elements)
    except github.GithubException as e:
        log.error("Failed to create the top-level git tree object")
        log.error("Reason: %s", e)
        log.error("Rolling back created repo...")

        delete_repo(new_repo)
        return None

    # Create commit linking to top of tree
    try:
        new_commit = new_repo.create_git_commit('Added initial challenge submodules', tl_tree, [base_commit])
        head.edit(new_commit.sha)
    except github.GithubException as e:
        log.error("Failed to create commit object")
        log.error("Reason: %s", e)
        # TODO: delete trees and blobs
        return

    log.info("Repository ready: %s", new_repo.html_url)
