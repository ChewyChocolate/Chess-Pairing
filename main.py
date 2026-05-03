import os
import sys

# Color support
if os.name == 'nt':
    os.system('color')

class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    GRAY = '\033[90m'
    WHITE = '\033[97m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'

from player import Player
from tournament import Tournament, TournamentType
from errors import TournamentError


def print_colored(text: str, color: str = "", bold: bool = False, **kwargs):
    """Print text with color."""
    prefix = f"{Colors.BOLD}" if bold else ""
    suffix = Colors.RESET
    print(f"{prefix}{color}{text}{suffix}", **kwargs)


def clear_screen():
    """Cross-platform screen clear without flicker."""
    os.system('cls' if os.name == 'nt' else 'clear')


def get_standings_width(t: Tournament) -> int:
    """Calculate dynamic width for standings."""
    max_name_len = max(len(p.name) for p in t.players) if t.players else 12
    return max(max_name_len, 20)


def print_standings(t: Tournament):
    """Print color-coded standings."""
    width = get_standings_width(t)
    
    # Header
    header = f"\n{'Pos':<4} {'Name':<{width}} {'Score':<6} {'SB':<6} {'BH':<6}"
    print_colored(header, Colors.CYAN, bold=True)
    print(Colors.GRAY + "-" * (width + 30) + Colors.RESET)
    
    standings = t.get_standings()
    for i, p in enumerate(standings, 1):
        # Color position based on rank
        if i == 1:
            pos_color = Colors.YELLOW
        elif i == 2:
            pos_color = Colors.WHITE
        elif i == 3:
            pos_color = Colors.MAGENTA
        else:
            pos_color = ""
        
        # Build display name (without color codes for alignment)
        display_name = p.name if p.active else f"{p.name} (Withdrawn)"
        
        if not p.active:
            print_colored(f"{i:<4} {display_name:<{width}} {p.score:<6.1f} {p.sonneborn_berger:<6.2f} {p.buchholz:<6.1f}", Colors.GRAY)
        else:
            print_colored(f"{i:<4}", pos_color, bold=True, end="")
            print(f" {display_name:<{width}} {p.score:<6.1f} {p.sonneborn_berger:<6.2f} {p.buchholz:<6.1f}")


def print_help():
    """Print help menu."""
    print_colored("\n=== Available Commands ===", Colors.CYAN, bold=True)
    print(f"""
  {Colors.GREEN}n{Colors.RESET} - Next round / Enter results
  {Colors.GREEN}r{Colors.RESET} - View/edit past rounds
  {Colors.GREEN}a{Colors.RESET} - Add new player
  {Colors.GREEN}w{Colors.RESET} - Withdraw player
  {Colors.GREEN}u{Colors.RESET} - Undo last result
  {Colors.GREEN}e{Colors.RESET} - Export CSV/HTML
  {Colors.GREEN}s{Colors.RESET} - Save tournament
  {Colors.GREEN}h{Colors.RESET} - Show this help
  {Colors.GREEN}f{Colors.RESET} - Change format (Round 1 only)
  {Colors.GREEN}q{Colors.RESET} - Quit
    """)


def confirm(prompt: str) -> bool:
    """Ask for confirmation."""
    response = input(f"{prompt} (y/n): ").strip().lower()
    return response == 'y'


def main():
    print_colored("=== Chess Tournament Pairing System ===", Colors.CYAN, bold=True)
    
    t = None
    save_file = "tournament_data.json"
    undo_stack = []  # For undo functionality
    
    if os.path.exists(save_file):
        choice = input(f"Found existing data in {save_file}. Load it? (y/n): ").lower()
        if choice == 'y':
            try:
                t = Tournament.load_from_file(save_file)
                print_colored(f"Loaded tournament: {t.name}", Colors.GREEN)
            except Exception as e:
                print_colored(f"Failed to load: {e}", Colors.RED)

    if not t:
        print("\nStarting NEW tournament.")
        print("Enter player names one by one. Type 'done' or leave blank when finished.")
        
        player_list = []
        while True:
            entry = input(f"Player {len(player_list) + 1} name: ").strip()
            if not entry or entry.lower() == 'done':
                if len(player_list) < 2:
                    print_colored("Error: You need at least 2 players to start a tournament.", Colors.RED)
                    continue
                break
            
            try:
                player_list.append(Player(entry))
            except TournamentError as e:
                print_colored(f"Error: {e}", Colors.RED)

        # Choose Tournament Type
        while True:
            fmt = input("\nChoose format: [1] Swiss, [2] Round Robin: ").strip()
            if fmt == '1':
                t_type = TournamentType.SWISS
                break
            elif fmt == '2':
                t_type = TournamentType.ROUND_ROBIN
                break
            print_colored("Invalid choice.", Colors.RED)

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
                    print_colored("Invalid input. Enter 'a' or a number.", Colors.RED)
        t.save_to_file(save_file)

    print_help()

    # Main Loop
    while True:
        clear_screen()
        print_standings(t)
        print(f"\n{Colors.BOLD}Tournament: {t.name}{Colors.RESET} ({t.t_type.value})")
        remaining = t.total_rounds - t.current_round_num
        print(f"Round {t.current_round_num} of {t.total_rounds} ({max(0, remaining)} remaining)")
        
        cmds = ["n-ext", "r-ounds", "a-dd", "w-ithdraw", "u-ndo", "e-xport", "s-ave", "h-elp"]
        if t.current_round_num <= 1:
            cmds.append("f-ormat")
        cmds.append("q-uit")
        
        print(f"\nCommands: {', '.join(cmds)}")
        
        cmd = input("\nChoice: ").lower().strip()
        
        if cmd in ('h', 'help', '?'):
            print_help()
            input("\nPress Enter to continue...")
            continue
        
        if cmd == 'f' and t.current_round_num <= 1:
            if t.rounds and any(m.result is not None for m in t.rounds[0]):
                print_colored("Error: Cannot change format after results have been recorded.", Colors.RED)
                input("\nPress Enter...")
                continue
                
            new_type = TournamentType.ROUND_ROBIN if t.t_type == TournamentType.SWISS else TournamentType.SWISS
            if confirm(f"Switch to {new_type.value}? This will reset current pairings"):
                t.t_type = new_type
                t.rounds = []
                t.current_round_num = 0
                if hasattr(t, '_rr_schedule'):
                    delattr(t, '_rr_schedule')
                
                if t.t_type == TournamentType.SWISS:
                    while True:
                        choice = input(f"Swiss Rounds - [A]uto ({t.total_rounds}) or enter a number: ").strip().lower()
                        if not choice or choice == 'a':
                            t.total_rounds = None
                            break
                        try:
                            t.total_rounds = int(choice)
                            break
                        except ValueError:
                            print_colored("Invalid input.", Colors.RED)
                
                print_colored(f"Switched to {new_type.value}.", Colors.GREEN)
                t.save_to_file(save_file)
            input("\nPress Enter...")
            continue

        if cmd in ('q', 'quit', 'exit'):
            if confirm("Save before quitting"):
                t.save_to_file(save_file)
            break
            
        elif cmd in ('s', 'save'):
            t.save_to_file(save_file)
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            print_colored(f"✓ Saved at {timestamp}!", Colors.GREEN, bold=True)

        elif cmd in ('e', 'export'):
            t.export_csv("standings.csv")
            t.export_html("standings.html")
            print_colored("Exported to standings.csv and standings.html", Colors.GREEN)

        elif cmd in ('a', 'add'):
            name = input("New player name: ").strip()
            if name:
                try:
                    p = Player(name)
                    t.add_player(p)
                    print_colored(f"Added {name} to the tournament pool.", Colors.GREEN)
                    t.save_to_file(save_file)
                except TournamentError as e:
                    print_colored(f"Error: {e}", Colors.RED)

        elif cmd in ('w', 'withdraw'):
            print("\nSelect player to withdraw:")
            active_players = [p for p in t.players if p.active]
            for i, p in enumerate(active_players, 1):
                print(f"  {i}. {p.name}")
            
            try:
                idx = int(input("Enter number: ")) - 1
                if 0 <= idx < len(active_players):
                    if confirm(f"Withdraw {active_players[idx].name}?"):
                        active_players[idx].active = False
                        print_colored(f"{active_players[idx].name} has been withdrawn.", Colors.YELLOW)
                        t.save_to_file(save_file)
            except ValueError:
                print_colored("Invalid input.", Colors.RED)
            
            input("\nPress Enter...")
            
        elif cmd in ('u', 'undo'):
            if not undo_stack:
                print_colored("Nothing to undo.", Colors.YELLOW)
            else:
                last_match, last_result = undo_stack.pop()
                last_match.result = None
                t.recalculate_state()
                t.save_to_file(save_file)
                print_colored("Undone last result.", Colors.GREEN)
            input("\nPress Enter...")

        elif cmd in ('r', 'rounds'):
            if not t.rounds:
                print_colored("No rounds have been generated yet.", Colors.YELLOW)
                input("\nPress Enter to continue...")
                continue
            
            while True:
                clear_screen()
                print_colored("--- Tournament Rounds ---", Colors.CYAN, bold=True)
                for i in range(len(t.rounds)):
                    status = ""
                    if t.rounds[i] and all(m.result is not None for m in t.rounds[i]):
                        status = Colors.GREEN + " [Complete]" + Colors.RESET
                    elif t.rounds[i] and any(m.result is None for m in t.rounds[i]):
                        status = Colors.YELLOW + " [In Progress]" + Colors.RESET
                    print(f"  [{i+1}] Round {i+1}{status}")
                print(f"\n[{Colors.BOLD}b{Colors.RESET}] Back to main menu")
                
                r_choice = input("\nSelect Round # to view/edit: ").strip().lower()
                if r_choice == 'b':
                    break
                
                try:
                    r_idx = int(r_choice) - 1
                    if 0 <= r_idx < len(t.rounds):
                        selected_round = t.rounds[r_idx]
                        while True:
                            clear_screen()
                            print_colored(f"--- Round {r_idx + 1} Boards ---", Colors.CYAN, bold=True)
                            for b_idx, m in enumerate(selected_round, 1):
                                if m.result:
                                    res_color = Colors.GREEN if m.result.value == "1-0" else Colors.RED if m.result.value == "0-1" else Colors.YELLOW
                                    res_str = f"[{res_color}{m.result.value}{Colors.RESET}]"
                                else:
                                    res_str = f"[{Colors.YELLOW}PENDING{Colors.RESET}]"
                                print(f"  Board {b_idx}: {m} {res_str}")
                            
                            print(f"\n[{Colors.BOLD}b{Colors.RESET}] Back to round selection")
                            
                            b_choice = input("\nSelect Board # to edit: ").strip().lower()
                            if b_choice == 'b':
                                break
                            
                            try:
                                board_num = int(b_choice)
                                m_idx = board_num - 1
                                if 0 <= m_idx < len(selected_round):
                                    match = selected_round[m_idx]
                                    if match.is_bye:
                                        t.record_match_result(match, "1-0 (BYE)")
                                        undo_stack.append((match, "1-0 (BYE)"))
                                        print_colored("Bye result set.", Colors.GREEN)
                                    else:
                                        print(f"\nEditing Board {board_num}: {match.white.name} vs {match.black.name}")
                                        print(f"  {Colors.GREEN}[1]{Colors.RESET} 1-0 (White wins)")
                                        print(f"  {Colors.RED}[2]{Colors.RESET} 0-1 (Black wins)")
                                        print(f"  {Colors.YELLOW}[3]{Colors.RESET} 1/2-1/2 (Draw)")
                                        print(f"  {Colors.GRAY}[0]{Colors.RESET} Reset to PENDING")
                                        
                                        shortcut_map = {"1": "1-0", "2": "0-1", "3": "1/2-1/2", "0": None}
                                        res_input = input("Result: ").strip().lower()
                                        
                                        if res_input == "0":
                                            match.result = None
                                            t.recalculate_state()
                                        elif res_input in shortcut_map:
                                            res = shortcut_map[res_input]
                                            t.record_match_result(match, res)
                                            undo_stack.append((match, res))
                                        else:
                                            print_colored("Invalid choice.", Colors.RED)
                                            continue
                                        
                                        t.save_to_file(save_file)
                                        print_colored("Result saved!", Colors.GREEN)
                                else:
                                    print_colored("Invalid board number.", Colors.RED)
                            except ValueError:
                                print_colored("Invalid input.", Colors.RED)
                    else:
                        print_colored("Invalid round number.", Colors.RED)
                except ValueError:
                    print_colored("Invalid input.", Colors.RED)

        elif cmd in ('n', 'next'):
            # Check if there's an ongoing round with pending results
            current_pairings = None
            if t.rounds:
                last_round = t.rounds[-1]
                if any(m.result is None for m in last_round):
                    current_pairings = last_round
            
            if not current_pairings:
                try:
                    current_pairings = t.generate_next_round()
                    undo_stack.clear()  # New round, clear undo stack
                except Exception as e:
                    print_colored(f"Error generating pairings: {e}", Colors.RED)
                    continue
            
            while True:
                clear_screen()
                print_colored(f"--- Round {t.current_round_num} Boards ---", Colors.CYAN, bold=True)
                
                pending_count = 0
                for i, m in enumerate(current_pairings, 1):
                    if m.result:
                        res_color = Colors.GREEN if m.result.value == "1-0" else Colors.RED if m.result.value == "0-1" else Colors.YELLOW
                        res_str = f"[{res_color}{m.result.value}{Colors.RESET}]"
                    else:
                        pending_count += 1
                        res_str = f"[{Colors.YELLOW}PENDING{Colors.RESET}]"
                    print(f"  Board {i}: {m} {res_str}")
                
                if pending_count == 0:
                    print_colored("\nAll results for this round recorded!", Colors.GREEN)
                    t.save_to_file(save_file)
                    break
                
                print(f"\n{Colors.YELLOW}{pending_count} match(es) pending{Colors.RESET}")
                print(f"\n[{Colors.BOLD}b{Colors.RESET}] Back to menu")
                print(f"[{Colors.BOLD}# Result{Colors.RESET}] Enter result (e.g., '2 1' = Board 2, Black wins)")
                
                choice_raw = input("\nChoice: ").strip().lower()
                if choice_raw == 'b':
                    break
                
                parts = choice_raw.split()
                try:
                    board_num = int(parts[0])
                    board_idx = board_num - 1
                    
                    if 0 <= board_idx < len(current_pairings):
                        match = current_pairings[board_idx]
                        if match.result:
                            print_colored(f"Board {board_num} already has a result.", Colors.YELLOW)
                            continue
                            
                        if match.is_bye:
                            t.record_match_result(match, "1-0")
                            undo_stack.append((match, "1-0"))
                            print_colored("Bye recorded.", Colors.GREEN)
                        else:
                            shortcut_map = {
                                "1": "1-0", "w": "1-0", "10": "1-0",
                                "2": "0-1", "b": "0-1", "01": "0-1",
                                "3": "1/2-1/2", "d": "1/2-1/2", "h": "1/2-1/2", "0.5": "1/2-1/2"
                            }
                            
                            if len(parts) > 1:
                                res_input = parts[1]
                            else:
                                print(f"\nMatch: {match.white.name} (White) vs {match.black.name} (Black)")
                                print(f"  {Colors.GREEN}[1/w/10]{Colors.RESET} White wins")
                                print(f"  {Colors.RED}[2/b/01]{Colors.RESET} Black wins")
                                print(f"  {Colors.YELLOW}[3/d/h/0.5]{Colors.RESET} Draw")
                                res_input = input("Result: ").strip().lower()
                            
                            res = shortcut_map.get(res_input, res_input)
                            if res:
                                t.record_match_result(match, res)
                                undo_stack.append((match, res))
                                print_colored("Result saved!", Colors.GREEN)
                            else:
                                print_colored("Invalid result.", Colors.RED)
                                continue
                        t.save_to_file(save_file)
                    else:
                        print_colored("Invalid board number.", Colors.RED)
                except (ValueError, IndexError):
                    print_colored("Invalid input format. Use 'Board# Result' (e.g., '2 1')", Colors.RED)
                except TournamentError as e:
                    print_colored(f"Error: {e}", Colors.RED)

        else:
            print_colored("Unknown command. Type 'h' for help.", Colors.YELLOW)


if __name__ == "__main__":
    main()