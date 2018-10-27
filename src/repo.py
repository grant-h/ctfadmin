import logging
import github

log = logging.getLogger(__name__)

def delete_repo(repo):
    try:
        repo.delete()
        log.info("Succesfully deleted repo '%s'", repo.name)
        return True
    except github.GithubException as e:
        log.error("Failed to rollback repo creation '%s'. Please manually delete.", str(repo))
        log.error("Reason: %s", str(e))
        return False

def create_repo(org, repo_name, manager_user, desc, admin_user=None):
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
    try:
        new_repo.add_to_collaborators(manager_user, 'push')
    except github.GithubException as e:
        log.error("Unable to add collaborator '%s' to repository '%s'",
                manager_user.username, repo_name)
        log.error("Reason: %s", str(e))
        log.error("Rolling back created repo...")

        delete_repo(new_repo)

        return None

    log.info("Successfully created repository and associated user account")

    return new_repo

def get_challenge_repos(config, org):
    # Get all of the existing challenge repos, if any
    challenge_repos = []
    for repo in org.get_repos():
        if repo.name.startswith(config.prefix):
            challenge_repos += [repo]

    log.debug('Found %d existing challenge repositories' % len(challenge_repos))

    return challenge_repos
