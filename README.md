# Chess Pairing

A TUI tournament pairing system supporting Swiss and Round Robin formats.

## Quick start

```bash
pip install textual
python3 main.py
```

First launch shows a setup screen: load an existing tournament or create a new one by entering player names and choosing a format.

## Commands

| Key | Action |
|-----|--------|
| `n` | Next round / enter result mode |
| `r` | Review past rounds |
| `a` | Add a new player |
| `w` | Withdraw a player |
| `u` | Undo last result |
| `d` | Delete last round |
| `z` | Create backup snapshot |
| `e` | Export standings (CSV + HTML) |
| `s` | Save tournament |
| `q` | Quit (with save prompt) |

In result mode (press `n` after generating a round):

| Key | Action |
|-----|--------|
| `1` / `w` | White wins |
| `2` / `b` | Black wins |
| `3` / `d` | Draw |
| `Esc` | Exit result mode |

Cursor auto-advances to the next pending board after each result.

## Formats

- **Swiss** — players are paired with opponents of similar score. Auto-calculates
  `ceil(log2(n))` rounds. Custom round count can be set at creation.
- **Round Robin** — every player plays every other player once.

## Requirements

Python 3.10+ and `textual>=8.0.0`.

## Tests

```bash
python3 -m unittest discover -v
```
