import sys
import argparse
import requests
import logging
import readline
import shlex

try:
    from IPython import embed
except ImportError:
    def embed():
        pass

import github
from github import Github

from cmds import *

__version__ = "0.1.0"
HISTORY_FILENAME = ".ctfadmin"

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# So we can add attributes to dicts
class ConfigDict(dict):
    pass

def github_init(organization, token):
    log.info("Loading organization '%s'", organization)

    # First create a Github instance using an access token
    gh = Github(token)

    try:
        org = gh.get_organization(organization)
    except requests.exceptions.InvalidHeader as e:
        log.error('Unable to get the organization page: %s', str(e))
        log.error('your token file is probably not correct')
        return None, None

    except github.GithubException as e:
        log.error('Unable to get the organization page: %s', str(e))
        log.error('Double check that you have access to the organization and that your token is valid')
        return None, None

    return org, gh

def load_configuration(filename):
    try:
        config = open(filename).read()
    except IOError:
        log.error("You need to create a configuration file as '%s'", args.config)
        return None

    # evaluate the configuration file (please dont run ctfadmin on untrusted configs)
    try:
        config = eval(config)
    except Exception as e:
        log.error('Your configuration file is malformed: %s', str(e))
        return None

    # make it easier to use
    config_n = ConfigDict()

    for k,v in config.iteritems():
        setattr(config_n, k, v)
        config_n[k] = v

    config = config_n

    required_fields = [
        {"key" : "categories", "ty" : list},
        {"key" : "organization", "ty" : str},
        {"key" : "admin_team", "ty" : str},
        {"key" : "variable", "ty" : list},
        {"key" : "template_dir", "ty" : str},
        {"key" : "ctfname", "ty" : str},
        {"key" : "prefix", "ty" : str},
    ]

    error = False
    # Validate the fields and types
    for field in required_fields:
        if field["key"] not in config:
            error = True
            log.error("Configuration file is missing required field '%s' (%s)",
                    field["key"], field["ty"])
        else:
            ft = type(config[field["key"]])
            if ft != field["ty"]:
                error = True
                log.error("Configuration file type mismatch for field '%s' (expected %s, got %s)",
                        field["key"], repr(field["ty"]), repr(ft))

    if not error:
        return config
    else:
        return None

def main():
    print('CTFAdmin (v%s)' % __version__)

    parser = argparse.ArgumentParser()
    parser.add_argument('--token-file', help="The file containing your GitHub personal token.",
        default="github.key")
    parser.add_argument('--config', help="The file containing your CTF configuration.",
        default="config.py")
    parser.add_argument('command', nargs=argparse.REMAINDER)

    args = parser.parse_args()

    try:
        token = open(args.token_file).read().strip()
    except IOError:
        log.error("You need to create a GitHub personal token and save it in the file '%s'", args.token_file)
        return 1

    config = load_configuration(args.config)

    if config is None:
        return 1

    org, gh = github_init(config.organization, token)

    if org is None or gh is None:
        return 1

    commands = [
            {'name' : 'create', 'handler': cmd_create, 'parser': cmd_create_parser},
            {'name' : 'list', 'handler': cmd_list, 'parser': cmd_list_parser},
            {'name' : 'delete', 'handler': cmd_delete, 'parser': cmd_delete_parser},
            {'name' : 'stats', 'handler': cmd_stats, 'parser': cmd_stats_parser},
    ]

    def dispatch_command(user_cmd, args):
        ret = None

        for cmd in commands:
            if user_cmd == cmd["name"]:
                try:
                    args = cmd["parser"].parse_args(args)
                    ret = cmd["handler"](config, gh, org, args)
                    return 0
                except IOError as exc:
                    if exc.message:
                        print(exc.message)

                    return 1

        print("Unknown command '%s'" % (user_cmd))
        return 1

    # Non-interactive command dispatch
    if len(args.command):
        return dispatch_command(args.command[0], args.command[1:])

    try:
        readline.read_history_file(HISTORY_FILENAME)
    except IOError:
        pass

    # Interactive command loop
    while True:
        try:
            action = raw_input('ctfadmin> ')
        except EOFError:
            break

        action = action.strip().rstrip()
        args = shlex.split(action)

        if len(args) > 0:
            user_cmd = args[0]
            args = args[1:]
        # no input? skip
        else:
            continue

        readline.write_history_file(HISTORY_FILENAME)

        # handle built-in commands
        if user_cmd in ['?', 'help']:
            if len(args) >= 1:
                found = False
                for cmd in commands:
                    if cmd["name"] == args[0]:
                        print('%s' % (cmd["parser"].format_help().split("\n")[0][7:]))
                        found = True
                        break

                if not found:
                    print("Unknown command '%s'" % (args[0]))
            else:
                for cmd in commands:
                    print('%s' % (cmd["parser"].format_help().split("\n")[0][7:]))
        elif user_cmd == "ipython":
            embed()
        elif user_cmd in ["exit", "quit"]:
            break
        else:
            dispatch_command(user_cmd, args)

    return 0

if __name__ == "__main__":
    sys.exit(main())
