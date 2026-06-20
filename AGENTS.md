# Project Overview

An extension for [Fava](https://github.com/beancount/fava), the front-end for [Beancount](https://github.com/beancount/beancount/), that support making bulk-edits, saving them and re-applying them at a later date.
The extension doesn't have a transaction edit UI, instead it hooks onto the Fava slice editor API endpoints to detect the last change made by the user, which can then be applied to a set of transactions.

The UX flow is:
  - Edit a transaction using the slice editor anywhere in Fava
  - Go to the extension, preview/confirm the last edit, then update the filters to bulk-edit a number of transactions
  - And / or save the edit and filter combo for later re-use
  - When importing new transactions into the ledger, apply all the saved 'replays' in bulk.
  
  
The extension uses [DeepDiff](https://pypi.org/project/deepdiff/) to make a json object of the changes in the edit and replay them, or save them in a yaml file for later re-applying. 


# Build / running

Use the venv at ~/Workspace/fava/.venv to run any test commands, all required modules are installed there. This module is installed in editable mode.