# Preloop CLI
Using this command line tool is the quickest way to interact with your Preloop entities.

# Installation instructions
Use pip to install the CLI. It's recommended to do so in a virtual environment.
```
pip install preloop-cli
```

# Authentication
Use environment variables to store an API key generated in your account to authenticate with Preloop.
```
export PRELOOP_KEY_ID=<key_id>
export PRELOOP_SECRET=<secret>
```

# Commands
Start with `preloop --help` to display a list of commands. You can also use `--help` along with a command to display a list of possible arguments and options that can be used with the command.
```
preloop list-datasources --help
```