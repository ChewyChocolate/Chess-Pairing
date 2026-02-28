import os

from player import Player
from tournament import Tournament, TournamentType
from errors import TournamentError

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_standings(t: Tournament):
    print(f"\n{'Pos':<4} {'Name':<12} {'Score':<6} {'SB':<6} {'BH':<6}")
    print("-" * 42)
    for i, p in enumerate(t.get_standings(), 1):
        status = "" if p.active else " (Withdrawn)"
        print(f"{i:<4} {p.name + status:<12} {p.score:<6.1f} {p.sonneborn_berger:<6.2f} {p.buchholz:<6.1f}")

def main():
    print("=== Chess Tournament Pairing System ===")
    
    t = None
    save_file = "tournament_data.json"
    
    if os.path.exists(save_file):
        choice = input(f"Found existing data in {save_file}. Load it? (y/n): ").lower()
        if choice == 'y':
            try:
                t = Tournament.load_from_file(save_file)
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
            
            try:
                player_list.append(Player(entry))
            except TournamentError as e:
                print(f"Error: {e}")

        # Choose Tournament Type
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
        if t_type == TournamentType.SWISS:
            while True:
                choice = input(f"\nSwiss Rounds - [A]uto ({t.total_rounds}) or enter a number: ").strip().lower()
                if not choice or choice == 'a':
                    print(f"Using auto-calculated rounds: {t.total_rounds}")
                    break
                try:
                    t.total_rounds = int(choice)
                    break
                except ValueError:
                    print("Invalid input. Enter 'a' or a number.")
        t.save_to_file(save_file)

    # Main Loop
    while True:
        clear_screen()
        print_standings(t)
        print(f"\nTournament: {t.name} ({t.t_type.value})")
        remaining = t.total_rounds - t.current_round_num
        print(f"Round {t.current_round_num} of {t.total_rounds} ({max(0, remaining)} remaining)")
        
        cmds = ["[n]ext round", "[r]ounds", "[a]dd player", "[w]ithdraw", "[e]xport", "[s]ave"]
        if t.current_round_num <= 1:
            cmds.append("[f]ormat")
        cmds.append("[q]uit")
        print(f"Commands: {', '.join(cmds)}")
        
        cmd = input("Choice: ").lower()
        
        if cmd == 'f' and t.current_round_num <= 1:
            if t.rounds and any(m.result is not None for m in t.rounds[0]):
                print("Error: Cannot change format after results have been recorded.")
                input("\nPress Enter...")
                continue
                
            new_type = TournamentType.ROUND_ROBIN if t.t_type == TournamentType.SWISS else TournamentType.SWISS
            if input(f"Switch to {new_type.value}? This will reset current pairings. (y/n): ").lower() == 'y':
                t.t_type = new_type
                t.rounds = []
                t.current_round_num = 0
                if hasattr(t, '_rr_schedule'):
                    delattr(t, '_rr_schedule')
                
                # If switched TO Swiss, ask for rounds
                if t.t_type == TournamentType.SWISS:
                    while True:
                        choice = input(f"Swiss Rounds - [A]uto ({t.total_rounds}) or enter a number: ").strip().lower()
                        if not choice or choice == 'a':
                            t.total_rounds = None # Reset to auto
                            break
                        try:
                            t.total_rounds = int(choice)
                            break
                        except ValueError:
                            print("Invalid input.")
                
                print(f"Switched to {new_type.value}.")
                t.save_to_file(save_file)
                input("\nPress Enter...")
            continue

        if cmd == 'q':
            if input("Save before quitting? (y/n): ").lower() == 'y':
                t.save_to_file(save_file)
            break
            
        elif cmd == 's':
            t.save_to_file(save_file)

        elif cmd == 'e':
            t.export_csv("standings.csv")
            t.export_html("standings.html")

        elif cmd == 'a':
            name = input("New player name: ").strip()
            if name:
                p = Player(name)
                t.add_player(p)
                print(f"Added {name} to the tournament pool.")
                t.save_to_file(save_file)

        elif cmd == 'w':
            print("\nSelect player to withdraw:")
            active_players = [p for p in t.players if p.active]
            for i, p in enumerate(active_players, 1):
                print(f"{i}. {p.name}")
            try:
                idx = int(input("Enter number: ")) - 1
                if 0 <= idx < len(active_players):
                    active_players[idx].active = False
                    print(f"{active_players[idx].name} has Been withdrawn.")
                    t.save_to_file(save_file)
            except ValueError:
                print("Invalid input.")
            
        elif cmd == 'r':
            if not t.rounds:
                print("No rounds have been generated yet.")
                input("\nPress Enter to continue...")
                continue
            
            while True:
                clear_screen()
                print("--- Tournament Rounds ---")
                for i in range(len(t.rounds)):
                    print(f"[{i+1}] Round {i+1}")
                print("[b] Back")
                
                r_choice = input("\nSelect Round # to view/edit: ").strip().lower()
                if r_choice == 'b':
                    break
                
                try:
                    r_idx = int(r_choice) - 1
                    if 0 <= r_idx < len(t.rounds):
                        selected_round = t.rounds[r_idx]
                        while True:
                            clear_screen()
                            print(f"--- Round {r_idx + 1} Boards ---")
                            for b_idx, m in enumerate(selected_round, 1):
                                res_str = f"[{m.result.value}]" if m.result else "[PENDING]"
                                print(f"Board {b_idx}: {m} {res_str}")
                            
                            b_choice = input("\nSelect Board # to edit, or 'b' to go back: ").strip().lower()
                            if b_choice == 'b':
                                break
                            
                            try:
                                board_num = int(b_choice)
                                m_idx = board_num - 1
                                if 0 <= m_idx < len(selected_round):
                                    match = selected_round[m_idx]
                                    if match.is_bye:
                                        t.record_match_result(match, "1-0 (BYE)")
                                        print("Bye result set.")
                                    else:
                                        print(f"\nEditing Board {board_num}: {match.white.name} vs {match.black.name}")
                                        print("  [1] 1-0  [2] 0-1  [3] 1/2-1/2  [0] Reset to PENDING")
                                        shortcut_map = {
                                            "1": "1-0", "2": "0-1", "3": "1/2-1/2", "0": None
                                        }
                                        res_input = input("New Result Choice: ").strip().lower()
                                        if res_input == "0":
                                            match.result = None
                                            t.recalculate_state()
                                        else:
                                            res = shortcut_map.get(res_input, res_input)
                                            t.record_match_result(match, res)
                                    t.save_to_file(save_file)
                                else:
                                    print("Invalid board number.")
                            except ValueError:
                                print("Invalid input.")
                    else:
                        print("Invalid round number.")
                except ValueError:
                    print("Invalid input.")

        elif cmd == 'n':
            # Check if there's an ongoing round with pending results
            current_pairings = None
            if t.rounds:
                last_round = t.rounds[-1]
                if any(m.result is None for m in last_round):
                    current_pairings = last_round
            
            if not current_pairings:
                try:
                    current_pairings = t.generate_next_round()
                except Exception as e:
                    print(f"Error generating pairings: {e}")
                    continue
            
            while True:
                clear_screen()
                print(f"--- Round {t.current_round_num} Boards ---")
                pending_indices = []
                for i, m in enumerate(current_pairings, 1):
                    res_str = f"[{m.result.value}]" if m.result else "[PENDING]"
                    print(f"Board {i}: {m} {res_str}")
                    if not m.result:
                        pending_indices.append(i)
                
                if not pending_indices:
                    print("\nAll results for this round recorded.")
                    t.save_to_file(save_file)
                    break
                
                choice_raw = input("\nEnter Board #, or 'Board# Result' (e.g. '2 1'), or 'b': ").strip().lower()
                if choice_raw == 'b':
                    break
                
                parts = choice_raw.split()
                try:
                    board_num = int(parts[0])
                    board_idx = board_num - 1
                    
                    if 0 <= board_idx < len(current_pairings):
                        match = current_pairings[board_idx]
                        if match.result:
                            print(f"Board {board_num} already has a result.")
                            continue
                            
                        if match.is_bye:
                            t.record_match_result(match, "1-0")
                            print("Bye recorded.")
                        else:
                            shortcut_map = {
                                "1": "1-0", "w": "1-0", "10": "1-0",
                                "2": "0-1", "b": "0-1", "01": "0-1",
                                "3": "1/2-1/2", "d": "1/2-1/2", "h": "1/2-1/2", "0.5": "1/2-1/2"
                            }
                            
                            if len(parts) > 1:
                                res_input = parts[1]
                            else:
                                print(f"\nMatch: {match.white.name} vs {match.black.name}")
                                print("  [1] 1-0  [2] 0-1  [3] 1/2-1/2")
                                res_input = input("Result: ").strip().lower()
                            
                            res = shortcut_map.get(res_input, res_input)
                            t.record_match_result(match, res)
                        t.save_to_file(save_file)
                    else:
                        print("Invalid board number.")
                except (ValueError, IndexError):
                    print("Invalid input format.")
                except TournamentError as e:
                    print(f"Error: {e}")

if __name__ == "__main__":
    main()
