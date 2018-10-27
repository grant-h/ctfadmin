# CTFAdmin

A tool to help automate the creation and permissions of CTF challenge repositories.
This tool is used for SwampCTF 2019 to help distribute private, challenge-specific repositories for authors to commit to.
It was designed to be easily configurable for any CTF event with custom challenge categories and repository templates.

## Example usage

```
CTFAdmin (v0.1.0)
INFO: Loading organization 'swampctf'
ctfadmin> help
create [-h] --type TYPE --user USER
list [-h] [--type TYPE] [--details]
delete [-h] [--force] name
ctfadmin> list
swctf_pwn1 - category=pwn num=1
swctf_web1 - category=web num=1
swctf_misc1 - category=misc num=1
swctf_misc2 - category=misc num=2
ctfadmin> create --type rev --user grant-h
INFO: Creating repository swctf_rev1
INFO: Description: SwampCTF 2019 Reversing challenge. Assigned to Grant Hernandez (@grant-h).
INFO: Associating admin team 'SwampCTF' (2958310)
INFO: Successfully created repository and associated user account
INFO: Retrieved base commit on the master branch
INFO: Building file system tree for 'template/'
INFO: Walked 3 directories and 3 files (total bytes 7290)
INFO: Creating git trees...
INFO: Repository loaded with template files from 'template/'
ctfadmin> list --details
swctf_pwn1 - category=pwn num=1 commits=2 contributors=grant-h
swctf_web1 - category=web num=1 commits=2 contributors=grant-h
swctf_misc1 - category=misc num=1 commits=2 contributors=grant-h
swctf_misc2 - category=misc num=2 commits=2 contributors=grant-h
ctfadmin> exit
```

### Non-interactive usage
All commands that you can perform interactively (with the exception of built-in ones such as `help`) can be specified on the command line for scripting purposes.

For example:
```
$ ctfadmin list
CTFAdmin (v0.1.0)
INFO: Loading organization 'swampctf'
swctf_pwn1 - category=pwn num=1
swctf_web1 - category=web num=1
swctf_misc1 - category=misc num=1
swctf_misc2 - category=misc num=2
$ ctfadmin create --type misc --user grant-h
CTFAdmin (v0.1.0)
INFO: Loading organization 'swampctf'
INFO: Creating repository swctf_misc3
INFO: Description: SwampCTF 2019 Reversing challenge. Assigned to Grant Hernandez (@grant-h).
INFO: Associating admin team 'SwampCTF' (2958310)
INFO: Successfully created repository and associated user account
INFO: Retrieved base commit on the master branch
INFO: Building file system tree for 'template/'
INFO: Walked 3 directories and 3 files (total bytes 7290)
INFO: Creating git trees...
INFO: Repository loaded with template files from 'template/'
```

## Downloading and Using

You will need to have the appropriate permissions on a GitHub organization and [personal access token](https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/) with the scopes of `repo` and `delete_repo`. Save your personal access token to a file named `github.key` in the root directory of CTFAdmin.

CTFAdmin only has one external dependency, `PyGithub`. To get started, follow the commands below

```sh
git clone https://github.com/grant-h/ctfadmin.git
cd ctfadmin/
pip install -r requirements.txt
python src/ctfadmin.py
```

## TODO
* Create a setup.py file for installation
* Deploy to pypi
* Add feature to automatically collect all repositories as submodules to a master repo

