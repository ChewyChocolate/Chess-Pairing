import json
import os
import csv
from tournament import Tournament


def save_tournament(tournament: Tournament, filename: str):
    data = tournament.to_dict()
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


def load_tournament(filename: str) -> Tournament:
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} not found.")
    with open(filename, 'r') as f:
        data = json.load(f)
    return Tournament.from_dict(data)


def export_csv(tournament: Tournament, filename: str):
    standings = tournament.get_standings()
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Position', 'Name', 'Score', 'Buchholz', 'SB', 'Rating', 'RatingDiff'])
        for i, p in enumerate(standings, 1):
            writer.writerow([i, p.name, p.score, p.buchholz, p.sonneborn_berger,
                             p.rating, f"{p.rating_change:+.1f}"])
    print(f"Standings exported to {filename}")


def export_html(tournament: Tournament, filename: str):
    standings = tournament.get_standings()
    rows = ""
    for i, p in enumerate(standings, 1):
        color = "#4ade80" if p.rating_change > 0 else "#f87171" if p.rating_change < 0 else "inherit"
        rows += f"""
            <tr>
                <td>{i}</td>
                <td style="font-weight: bold;">{p.name}</td>
                <td>{p.score:.1f}</td>
                <td>{p.buchholz:.1f}</td>
                <td>{p.sonneborn_berger:.1f}</td>
                <td>{p.rating}</td>
                <td style="color: {color};">{p.rating_change:+.1f}</td>
            </tr>"""

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #f3f4f6; padding: 40px; }}
            table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            th, td {{ padding: 15px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
            th {{ background: #1f2937; color: white; }}
            h1 {{ color: #111827; }}
        </style>
    </head>
    <body>
        <h1>{tournament.name} - Standings</h1>
        <p>Type: {tournament.t_type.value} | Rounds: {tournament.current_round_num}</p>
        <table>
            <thead><tr><th>#</th><th>Player</th><th>Score</th><th>BH</th><th>SB</th><th>Rating</th><th>Elo Δ</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </body>
    </html>"""
    with open(filename, 'w') as f:
        f.write(html)
    print(f"Standings exported to {filename}")


def print_standings(tournament: Tournament):
    print(f"\n{'Pos':<4} {'Name':<12} {'Score':<6} {'BH':<6} {'Elo Δ':<8} {'Rating':<6}")
    print("-" * 55)
    for i, p in enumerate(tournament.get_standings(), 1):
        status = "" if p.active else " (Withdrawn)"
        print(f"{i:<4} {p.name + status:<12} {p.score:<6.1f} {p.buchholz:<6.1f} "
              f"{p.rating_change:<+8.1f} {p.rating:<6}")
