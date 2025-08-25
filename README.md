# Fava Edit Replay

A bulk edit extension for [Fava](https://beancount.github.io/fava/), the web interface for Beancount.

## What it does

This extension allows you to:
- Apply bulk edits to multiple Beancount transactions at once
- Save edit operations (a combination of search filters and a diff) as "replays" that can be applied later
- Filter transactions by account, time period, or custom filters
- Suggests filters based on last modified transaction

## Installation

```bash
pip install git+https://github.com/paulsc/fava-edit-replay
```

Don't forget to add the extension to your beancount file. The 'db' option specifies the path of the yaml database file containing your saved replays.
```bash
2000-11-11 custom "fava-extension" "fava_edit_replay" "{ 'db': 'my-replays.yaml' }"
```

## Usage

### As a Fava Extension

1. Add the extension to your Fava configuration
2. Use the web interface to create and apply bulk edits

### Command Line

Use the command line tool to apply all the replays to your ledger.
```bash
fava-edit-replay replays.yaml ledger.beancount
```
