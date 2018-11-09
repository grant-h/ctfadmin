{
    # Edit depending on your CTF
    "categories" : [
        {"short_name" : "pwn", "full_name": "Pwn"},
        {"short_name" : "rev", "full_name": "Reversing"},
        {"short_name" : "web", "full_name": "Web"},
        {"short_name" : "crypto", "full_name": "Cryptography"},
        {"short_name" : "for", "full_name": "Forensics"},
        {"short_name" : "misc", "full_name": "Miscellaneous"},
    ],

    # The GitHub organization where challenges will be held
    # This should have the ability to create private repositories!
    "organization" : "ctfadmins",

    # The GitHub organization team name which will administrate
    # the CTF. Optional: leave as ""
    "admin_team" : "PwnCTF",

    # The file paths which will support variable replacement
    "variable" : ['README.md'],

    # The git repository template directory
    "template_dir" : "template/",

    # DO NOT CHANGE THESE AFTER CREATING REPOS
    "ctfname" : "PwnCTF 2001",
    "prefix" : "pwctf_",
}
