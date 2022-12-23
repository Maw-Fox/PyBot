# PyBot
A local F-Chat bot framework built with Python.

## Usage:
`python pybot.py`

**Note:** You do not need to create a passphrase or store your passphrase-encrypted (*SHA512*) password on the filesystem, but it will require you to input your username and password either via the login wizard, or via the `--username` and `--password` arguments.

## Usage (Advanced):
`python pybot.py --username me --password qwerty --skip`
This command allows you to run the program without storing a creds.json file and skipping the passphrase query. Useful if you're a developer and developing a feature and want to quickly start the bot with one command.
