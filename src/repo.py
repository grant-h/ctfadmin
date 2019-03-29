import logging
import github
import re

log = logging.getLogger(__name__)

object_types = {
        'directory' : '040000',
        'file' : '100644',
        'executable' : '100755',
        'submodule' : '160000',
        # XXX: we do not support symlinks
        # https://developer.github.com/v3/git/trees/#create-a-tree
}

class GitSubmodule(object):
    def __init__(self, path, url, branch, commit):
        self.path = path
        self.url = url
        self.branch = branch
        self.commit = commit

    def __str__(self):
        return """
[submodule "%s"]
\tpath = %s
\turl = %s
\tbranch = %s""" % (self.path, self.path, self.url, self.branch)

def delete_repo(repo):
    try:
        repo.delete()
        log.info("Succesfully deleted repo '%s'", repo.name)
        return True
    except github.GithubException as e:
        log.error("Failed to rollback repo creation '%s'. Please manually delete.", str(repo))
        log.error("Reason: %s", str(e))
        return False

def create_repo(org, repo_name, desc, manager_user=None, admin_user=None):
    log.info('Creating repository %s', repo_name)
    log.info('Description: %s', desc)

    if admin_user:
        log.info("Associating admin team '%s' (%d)",
                admin_user.name, admin_user.id)
        team_id = admin_user.id

    # Actually create the repository
    try:
        new_repo = org.create_repo(
            name=repo_name,
            description=desc,
            private=True,
            has_wiki=False,
            team_id=team_id,
            has_downloads=False,
            has_projects=False,
            auto_init=True # we need to auto_init, otherwise we cannot create an initial commit
        )
    except github.GithubException as e:
        log.error("Unable to create repository '%s'", repo_name)
        log.error("Reason: %s", str(e))
        return None

    # Add a single collaborator to with push access to the new repository
    if manager_user:
        try:
            new_repo.add_to_collaborators(manager_user, 'push')
        except github.GithubException as e:
            log.error("Unable to add collaborator '%s' to repository '%s'",
                    manager_user.username, repo_name)
            log.error("Reason: %s", str(e))
            log.error("Rolling back created repo...")

            delete_repo(new_repo)

            return None
        log.info("Successfully created repository %s", repo_name)
    else:
        log.info("Successfully created repository %s and associated user account", repo_name)

    return new_repo

def validate_category(config, category):
    for cat in config.categories:
        if category == cat["short_name"] or category == cat["full_name"]:
            return cat

    return None

def get_challenge_repos(config, org):
    # Get all of the existing challenge repos, if any
    challenge_repos = []
    for repo in org.get_repos():
        name = repo.name
        match = re.match(config.prefix + r'([a-zA-Z]+)([0-9]+)', name)

        if not match:
            continue

        # pimp the repo object with swampctf specific stuff
        repo.category = match.group(1)

        if validate_category(config, repo.category) is None:
            log.warning("Malformed CTF repository '%s': invalid category '%s'", name, repo.category)
            continue

        repo.chal_num = int(match.group(2))

        challenge_repos += [repo]

    log.debug('Found %d existing challenge repositories' % len(challenge_repos))

    repos_sorted = sorted(challenge_repos, key=lambda x: x.name)

    return repos_sorted
