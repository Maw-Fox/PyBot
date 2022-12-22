# PyBot
A local F-Chat bot framework built with Python.

## Usage:
`python pybot.py --username me --password qwerty`

Alternatively, you can use a `creds.json` in the main repository folder and use the structure:
```
{
    "username": "me",
    "password": "qwerty"
}
```

You may also use the `--makecreds` command argument in order to create a `creds.json` so you do not need to explicitly use command argument credentials every time you start the bot.

The program will salt and do extremely rudimentary cryptography to make sure the password is not stored as plaintext during its launch. Keep in mind, this is VERY insecure but it does make it so that potential people viewing your files can't just see your password in full without performing the reversal process. It would be far more secure if the FChat/FList API allowed you to input keys and digests into a password field, but unfortunately this is not the case as it stands currently.
