# PyBot
A local F-Chat bot framework built with Python.

## Usage (First Time):
`python pybot.py --username me --password qwerty`

**Note:** You do not need to create a passphrase or store your passphrase-encrypted password on the filesystem, but it will require you to set the above command arguments every time you launch the bot.

Once you have a `creds.json` file created and a passphrase set, you do not require credentials on your launch arguments. Upon the next launch of the bot, you can just input your passphrase in order to decrypt your encrypted password that is stored on the local disk.