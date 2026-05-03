import os
from models import Player, TournamentType, TournamentError
from tournament import Tournament
from tournament_io import save_tournament, load_tournament, export_csv, export_html, print_standings

SAVE_FILE = "tournament_data.json"
CSV_FILE = "standings.csv"
HTML_FILE = "standings.html"


def main():
    print("=== Chess Tournament Pairing System ===")

    t = None

    if os.path.exists(SAVE_FILE):
        choice = input(f"Found existing data in {SAVE_FILE}. Load it? (y/n): ").lower()
        if choice == 'y':
            try:
                t = load_tournament(SAVE_FILE)
                print(f"Loaded tournament: {t.name}")
            except Exception as e:
                print(f"Failed to load: {e}")

    if not t:
        print("\nStarting NEW tournament.")
        print("Enter player names one by one. Type 'done' or leave blank when finished.")

        player_list = []
        while True:
            entry = input(f"Player {len(player_list) + 1} name: ").strip()
            if not entry or entry.lower() == 'done':
                if len(player_list) < 2:
                    print("Error: You need at least 2 players to start a tournament.")
                    continue
                break

            if ',' in entry:
                parts = entry.split(',')
                name = parts[0].strip()
                try:
                    rating = int(parts[1].strip() or "1500")
                except ValueError:
                    rating = 1500
            else:
                name, rating = entry, 1500

            try:
                player_list.append(Player(name, rating))
            except TournamentError as e:
                print(f"Error: {e}")

        while True:
            fmt = input("\nChoose format: [1] Swiss, [2] Round Robin: ")
            if fmt == '1':
                t_type = TournamentType.SWISS
                break
            elif fmt == '2':
                t_type = TournamentType.ROUND_ROBIN
                break
            print("Invalid choice.")

        t = Tournament("User Tournament", player_list, t_type=t_type)
        save_tournament(t, SAVE_FILE)

    while True:
        print_standings(t)
        print(f"\nTournament: {t.name} ({t.t_type.value})")
        print(f"Current Round: {t.current_round_num}")
        print("Commands: [n]ext round, [a]dd player, [w]ithdraw, "
              "[u]ndo match, [U]ndo round, [e]xport, [s]ave, [q]uit")
        cmd = input("Choice: ").lower()

        if cmd == 'q':
            if input("Save before quitting? (y/n): ").lower() == 'y':
                save_tournament(t, SAVE_FILE)
            break

        elif cmd == 's':
            save_tournament(t, SAVE_FILE)

        elif cmd == 'e':
            export_csv(t, CSV_FILE)
            export_html(t, HTML_FILE)

        elif cmd == 'a':
            name = input("New player name: ").strip()
            if name:
                try:
                    rating = int(input("Rating (default 1500): ") or "1500")
                except ValueError:
                    rating = 1500
                p = Player(name, rating)
                t.add_player(p)
                print(f"Added {name} to the tournament pool.")
                save_tournament(t, SAVE_FILE)

        elif cmd == 'w':
            print("\nSelect player to withdraw:")
            active_players = [p for p in t.players if p.active]
            for i, p in enumerate(active_players, 1):
                print(f"{i}. {p.name}")
            try:
                idx = int(input("Enter number: ")) - 1
                if 0 <= idx < len(active_players):
                    active_players[idx].active = False
                    print(f"{active_players[idx].name} has been withdrawn.")
                    save_tournament(t, SAVE_FILE)
            except ValueError:
                print("Invalid input.")

        elif cmd == 'u':
            m = t.undo_last_match()
            if m:
                print(f"Undid result of {m}")
                save_tournament(t, SAVE_FILE)
            else:
                print("Nothing to undo.")

        elif cmd == 'U':
            if t.undo_last_round():
                print(f"Undid round {t.current_round_num + 1}.")
                save_tournament(t, SAVE_FILE)
            else:
                print("No round to undo.")

        elif cmd == 'n':
            try:
                pairings = t.generate_next_round()
            except Exception as e:
                print(f"Error generating pairings: {e}")
                continue

            print("\n--- Pairings ---")
            for i, m in enumerate(pairings, 1):
                if m.is_bye:
                    print(f"  Match {i}: {m} (auto-recorded)")
                else:
                    print(f"  Match {i}: {m}")
            print("----------------")

            for i, m in enumerate(pairings, 1):
                if m.is_bye:
                    t.record_match_result(m, "1-0")
                    continue

                while True:
                    print(f"\nMatch {i}: {m}")
                    res = input("  Enter result (1-0, 0-1, 1/2-1/2): ").strip()
                    try:
                        t.record_match_result(m, res)
                        break
                    except TournamentError as e:
                        print(f"  Error: {e}")
            save_tournament(t, SAVE_FILE)
