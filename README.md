# Chess Pairing

A CLI tournament pairing system supporting Swiss and Round Robin formats.

## Quick start

```bash
python3 main.py
```

Follow the prompts to enter player names, choose a format, and start pairing.

## Commands

| Key | Action |
|-----|--------|
| `n` | Next round / enter results |
| `r` | View/edit past rounds |
| `a` | Add a new player |
| `w` | Withdraw a player |
| `u` | Undo last result |
| `e` | Export standings (CSV + HTML) |
| `s` | Save tournament |
| `h` | Show help |
| `f` | Change format (Round 1 only) |
| `q` | Quit |

Results can be entered with shortcuts: `1`/`w` = White wins, `2`/`b` = Black wins,
`3`/`d` = Draw. Combined format: `2 1` = Board 2, White wins.

## Formats

- **Swiss** — players are paired with opponents of similar score. Auto-calculates
  `ceil(log2(n))` rounds. Custom round count can be set at creation.
- **Round Robin** — every player plays every other player once.

## Requirements

Python 3.10+. Uses only the standard library — no third-party packages.

## Tests

```bash
python3 -m unittest discover -v
```
