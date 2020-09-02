# Readteam Notebook

Redteam Notebook is an experiment to address digital intelligence archiving on offensive engagements. It should be easy to take notes and screenshots, organize data, and import security tooling output from other common sources.

**NOTE:** This is currently alpha, and is not feature complete, but should work as an MVP.

## Setting it up

It is recommended to use a Python virtual environment (though it's not a requirement to do so.) You can follow the steps below.

### Using pipenv

Make sure you have pipenv installed. You can install with pip3 or your package manager before proceeding.

```
$ git clone https://github.com/unix-ninja/redteamnotebook.git
$ cd redteamnotebook/
$ pipenv --python 3
$ pipenv install -r requirements.txt
$ pipenv run python redteamnotebook.py
```

### Using python3 venv

Instead of a third party package like pipenv, you could try venv which is now built into Python 3. No additional setup is required.

```
$ git clone https://github.com/unix-ninja/redteamnotebook.git
$ cd redteamnotebook/
$ python3 -m venv .
$ source bin/activate
$ pip install -r requirements.txt
$ python redteamnotebook.py
```

> Note: For Python 3.8, please use the alternate requirements-3.8.txt file. This replaces libnmap with natlas-libnmap, as the former is not currently available for Python 3.8:

```
$ pipenv install -r requirements-3.8.txt
```

## Quick Start

Once you have launched Redteam Notebook, you should have a new, empty notebook up on your screen. The first thing you will want to do is add a new root node. Click on the "New Root Node" button in the toolbar. You should see a new node called 'Node' appear in the left pane. Click on that node, and now you can start placing notes in the right-hand pane.

You can add children nodes by clicking on a node and then using the 'New Node' button, or additional root nodes with the 'New Root Node' button again.

For more information, visit https://www.unix-ninja.com/p/introducing_redteam_notebook
