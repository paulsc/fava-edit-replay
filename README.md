# Fava Edit Replay

A bulk edit extension for [Fava](https://beancount.github.io/fava/), the web interface for Beancount.

## What it does

This extension allows you to:
- Apply bulk edits to multiple Beancount transactions at once
- Save edit operations as "replays" that can be applied later
- Filter transactions by account, time period, or custom filters
- Preview changes before applying them

## Installation

```bash
pip install -e .
```

## Usage

### As a Fava Extension

1. Add the extension to your Fava configuration
2. Use the web interface to create and apply bulk edits

### Command Line

```bash
fava-edit-replay replays.yaml ledger.beancount
```

## Development

Install with development dependencies:

```bash
pip install -e .[dev]
```

## License

[Add your license here] 