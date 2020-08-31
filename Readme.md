# Readteam Notebook

Redteam Notebook is an experiment to address digital intelligence archiving on offensive engagements. It should be easy to take notes and screenshots, organize data, and import security tooling output from other common sources.

**NOTE:** This is currently alpha, and is not feature complete, but should work as an MVP.

## Use

It is recommended to use a Python virtual environment (though it's not a requirement to do so.)

Using pipenv, you can follow these steps:

```
$ git clone https://github.com/unix-ninja/redteamnotebook.git
$ cd redteamnotebook/
$ pipenv --python 3
$ pipenv install -r requirements.txt
$ pipenv run python redteamnotebook.py
```

For more information, visit https://www.unix-ninja.com/p/introducing_redteam_notebook
