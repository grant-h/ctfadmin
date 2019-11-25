# CTFAdmin

A tool to help automate the creation and permissions of CTF challenge repositories.
This tool can be used by CTF administrators to help distribute private, challenge-specific GitHub repositories for authors to commit to.
It was designed to be easily configurable for any CTF event with custom challenge categories and repository templates.
Instead of manually provisioning challenge repos using bespoke shell scripts and the GitHub web interface, use or extend CTFAdmin to automate your actions and ensure a consistent experience for you and your challenge creators.

## Downloading and Using

You will need to have the appropriate permissions on a GitHub organization (with private repositories) and a [personal access token](https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/) with the scopes of `repo` and `delete_repo`. Save your personal access token to a file named `github.key` in the root directory of CTFAdmin.

CTFAdmin only has one external dependency, `PyGithub`. To get started, follow the commands below

```sh
git clone https://github.com/grant-h/ctfadmin.git
cd ctfadmin/
pip install -r requirements.txt
python src/ctfadmin.py
```

### Configuring for your CTF
To use CTFAdmin for your CTF, you need to edit the `config.py` file that ships with the repository. It contains information about what GitHub organization the challenges will be stored under and other metadata about the CTF such as, the name and the challenge categories.

## Commands (and future commands)

- [X] `create` - Creates a single challenge repository from a template directory
- [X] `list` - Lists all challenge repositories
- [X] `delete` - Removes a single challenge repository
- [X] `coalesce` - Creates and updates a single meta-repository containing submodules of all the challenges. Useful for challenge deployment and testing
- [X] `cleanup` - This is used after the CTF to remove all of the challenge repositories

## Example usage
Here is example usage of CTFAdmin in listing and creating a challenge repository.

```
CTFAdmin (v0.1.0)
INFO: Loading organization 'ctfadmins'
ctfadmin> help
create [-h] --type TYPE --user USER
list [-h] [--type TYPE] [--details]
delete [-h] [--force] name
stats [-h] {progress}
coalesce [-h]
cleanup [-h] [--i-solemnly-swear-i-am-up-to-no-good]
ctfadmin> list
pwctf_pwn1 - category=pwn num=1
pwctf_web1 - category=web num=1
pwctf_misc1 - category=misc num=1
pwctf_misc2 - category=misc num=2
ctfadmin> create --type rev --user grant-h
INFO: Creating repository pwctf_rev1
INFO: Description: ctfadmins 2019 Reversing challenge. Assigned to Grant Hernandez (@grant-h).
INFO: Associating admin team 'ctfadmins' (2958310)
INFO: Successfully created repository and associated user account
INFO: Retrieved base commit on the master branch
INFO: Building file system tree for 'template/'
INFO: Walked 3 directories and 3 files (total bytes 7290)
INFO: Creating git trees...
INFO: Repository loaded with template files from 'template/'
ctfadmin> list --details
pwctf_pwn1 - category=pwn num=1 commits=2 contributors=grant-h
pwctf_web1 - category=web num=1 commits=2 contributors=grant-h
pwctf_misc1 - category=misc num=1 commits=2 contributors=grant-h
pwctf_misc2 - category=misc num=2 commits=2 contributors=grant-h
ctfadmin> exit
```

### Non-interactive usage
All commands that you can perform interactively (with the exception of built-in ones such as `help`) can be specified on the command line for scripting purposes.

For example:
```
$ ctfadmin list
CTFAdmin (v0.1.0)
INFO: Loading organization 'ctfadmins'
pwctf_pwn1 - category=pwn num=1
pwctf_web1 - category=web num=1
pwctf_misc1 - category=misc num=1
pwctf_misc2 - category=misc num=2
$ ctfadmin create --type misc --user grant-h
CTFAdmin (v0.1.0)
INFO: Loading organization 'ctfadmins'
INFO: Creating repository pwctf_misc3
INFO: Description: ctfadmins 2019 Reversing challenge. Assigned to Grant Hernandez (@grant-h).
INFO: Associating admin team 'ctfadmins' (2958310)
INFO: Successfully created repository and associated user account
INFO: Retrieved base commit on the master branch
INFO: Building file system tree for 'template/'
INFO: Walked 3 directories and 3 files (total bytes 7290)
INFO: Creating git trees...
INFO: Repository loaded with template files from 'template/'
```

## TODO
* Create a setup.py file for installation
* Deploy to pypi
* Add feature to automatically collect all repositories as submodules to a master repo

