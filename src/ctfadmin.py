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
    g = Github(token)

    try:
        org = g.get_organization(organization)
    except requests.exceptions.InvalidHeader as e:
        log.error('Unable to get the organization page: %s', str(e))
        log.error('your token file is probably not correct')
        return None

    except github.GithubException as e:
        log.error('Unable to get the organization page: %s', str(e))
        log.error('Double check that you have access to the organization and that your token is valid')
        return None

    return org, g

def main():
    print('CTFAdmin (v%s)' % __version__)

    parser = argparse.ArgumentParser()
    parser.add_argument('--token-file', help="The file containing your GitHub personal token.",
        default="github.key")
    parser.add_argument('--config', help="The file containing your CTF configuration.",
        default="config.py")

    args = parser.parse_args()

    try:
        token = open(args.token_file).read().strip()
    except IOError:
        log.error("You need to create a GitHub personal token and save it in the file '%s'", args.token_file)
        return 1

    try:
        config = open(args.config).read()
    except IOError:
        log.error("You need to create a configuration file as '%s'", args.config)
        return 1

    # evaluate the configuration file
    try:
        config = eval(config)
    except Exception as e:
        log.error('Your configuration file is malformed: %s', str(e))
        return 1

    # make it easier to use
    config_n = ConfigDict()

    for k,v in config.iteritems():
        setattr(config_n, k, v)
        config_n[k] = v

    config = config_n

    # validate it
    config.variable = map(lambda x: os.path.join(config.template_dir, x), config.variable)

    org, g = github_init(config.organization, token)

    if org is None:
        return 1

    commands = [
            {'name' : 'create', 'handler': cmd_create, 'parser': cmd_create_parser},
            {'name' : 'list', 'handler': cmd_list, 'parser': cmd_list_parser},
            {'name' : 'delete', 'handler': cmd_delete, 'parser': cmd_delete_parser},
    ]

    try:
        readline.read_history_file(HISTORY_FILENAME)
    except IOError:
        pass

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
        else:
            continue

        readline.write_history_file(HISTORY_FILENAME)

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
            ret = None
            found = False
            for cmd in commands:
                if user_cmd == cmd["name"]:
                    try:
                        args = cmd["parser"].parse_args(args)
                        ret = cmd["handler"](config, g, org, args)
                    except IOError as exc:
                        if exc.message:
                            print(exc.message)

                    found = True
                    break

            if not found:
                print("Unknown command '%s'" % (user_cmd))

    return 0

if __name__ == "__main__":
    sys.exit(main())
