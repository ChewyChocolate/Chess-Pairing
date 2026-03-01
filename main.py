import random
import uuid
import json
import os
import csv
import math
from typing import List, Tuple, Optional, Set, Dict
from enum import Enum

class TournamentError(Exception):
    """Custom exception for tournament-related errors."""
    pass

class Result(Enum):
    WHITE_WIN = "1-0"
    BLACK_WIN = "0-1"
    DRAW = "1/2-1/2"
    BYE = "1-0 (BYE)"

class Player:
    def __init__(self, name: str, rating: int = 1500):
        if not name:
            raise TournamentError("Player name cannot be empty.")
        
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.rating = rating
        self.score = 0.0
        self.opponents: List['Player'] = []
        self.color_history: List[str] = []  # 'W' or 'B'
        self.bye_received = False
        self.active = True
        self.rating_change = 0.0 # New: Track Elo changes
        
        # Tie-break metrics
        self.buchholz = 0.0
        self.sonneborn_berger = 0.0

    def __repr__(self):
        return f"{self.name} ({self.score})"

    def update_tiebreaks(self):
        """Calculates standard chess tie-breaks."""
        self.buchholz = sum(opp.score for opp in self.opponents)
        
        sb = 0.0
        # This is strictly a simplification; real SB depends on the specific match result
        # For this demo, we'll assume standard SB: sum of scores of opponents you beat + 1/2 of those you drew
        # To do this accurately, we'd need to track match results per opponent. 
        # We'll stick to a robust Buchholz for now.
        self.sonneborn_berger = sb

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "rating": self.rating,
            "score": self.score,
            "opponent_ids": [opp.id for opp in self.opponents],
            "color_history": self.color_history,
            "bye_received": self.bye_received,
            "active": self.active,
            "rating_change": self.rating_change
        }

    @classmethod
    def from_dict(cls, data):
        p = cls(data["name"], data["rating"])
        p.id = data["id"]
        p.score = data["score"]
        p.color_history = data["color_history"]
        p.bye_received = data["bye_received"]
        p.active = data.get("active", True)
        p.rating_change = data.get("rating_change", 0.0)
        return p

class Match:
    def __init__(self, white: Optional[Player], black: Optional[Player], is_bye: bool = False):
        self.white = white
        self.black = black
        self.is_bye = is_bye
        self.result: Optional[Result] = None

    def to_dict(self):
        return {
            "white_id": self.white.id if self.white else None,
            "black_id": self.black.id if self.black else None,
            "is_bye": self.is_bye,
            "result": self.result.value if self.result else None
        }

    def __repr__(self):
        if self.is_bye:
            p = self.white or self.black
            return f"{p.name} [BYE]"
        res_str = f" [{self.result.value}]" if self.result else ""
        return f"{self.white.name} (W) vs {self.black.name} (B){res_str}"

class TournamentType(Enum):
    SWISS = "Swiss"
    ROUND_ROBIN = "Round Robin"

class Tournament:
    def __init__(self, name: str, players: List[Player], t_type: TournamentType = TournamentType.SWISS):
        self.name = name
        self.players = players
        self.t_type = t_type
        self.rounds: List[List[Match]] = []
        self.current_round_num = 0

    def add_player(self, player: Player):
        self.players.append(player)

    def get_standings(self) -> List[Player]:
        """Returns players sorted by score, then Buchholz, then rating."""
        for p in self.players:
            p.update_tiebreaks()
        return sorted(self.players, key=lambda p: (p.score, p.buchholz, p.rating), reverse=True)

    def record_match_result(self, match: Match, result_code: str):
        if match.result is not None:
            raise TournamentError("Match already has a result.")

        if match.is_bye:
            p = match.white or match.black
            p.score += 1.0
            p.bye_received = True
            match.result = Result.BYE
            return

        mapping = {
            "1-0": (Result.WHITE_WIN, 1.0, 0.0),
            "0-1": (Result.BLACK_WIN, 0.0, 1.0),
            "1/2-1/2": (Result.DRAW, 0.5, 0.5)
        }

        if result_code not in mapping:
            raise TournamentError(f"Invalid result: {result_code}")

        res_enum, w_pts, b_pts = mapping[result_code]
        match.result = res_enum
        
        # Elo Calculation (K=32)
        k = 32
        expected_w = 1 / (1 + 10 ** ((match.black.rating - match.white.rating) / 400))
        expected_b = 1 - expected_w
        
        diff_w = k * (w_pts - expected_w)
        diff_b = k * (b_pts - expected_b)
        
        match.white.rating_change += diff_w
        match.black.rating_change += diff_b
        
        # Update scores
        match.white.score += w_pts
        match.black.score += b_pts
        
        # Track history
        match.white.opponents.append(match.black)
        match.black.opponents.append(match.white)
        match.white.color_history.append('W')
        match.black.color_history.append('B')

    def generate_next_round(self) -> List[Match]:
        if self.t_type == TournamentType.SWISS:
            return self.generate_next_round_swiss()
        else:
            return self.generate_next_round_round_robin()

    def generate_communities_round_robin(self) -> List[List[Match]]:
        """Pre-generates all RR rounds."""
        n = len(self.players)
        temp_players = self.players[:]
        if n % 2 != 0:
            temp_players.append(None)
            n += 1
            
        all_rounds = []
        for r in range(n - 1):
            matches = []
            for i in range(n // 2):
                p1, p2 = temp_players[i], temp_players[n - 1 - i]
                if p1 and p2:
                    m = Match(p1, p2) if (i + r) % 2 == 0 else Match(p2, p1)
                    matches.append(m)
                elif p1 or p2:
                    matches.append(Match(p1 or p2, None, is_bye=True))
            all_rounds.append(matches)
            temp_players = [temp_players[0]] + [temp_players[-1]] + temp_players[1:-1]
        return all_rounds

    def generate_next_round_round_robin(self) -> List[Match]:
        if not hasattr(self, '_rr_schedule'):
            self._rr_schedule = self.generate_communities_round_robin()
            
        if self.current_round_num >= len(self._rr_schedule):
            raise TournamentError("All Round Robin rounds completed.")
            
        round_matches = self._rr_schedule[self.current_round_num]
        self.current_round_num += 1
        self.rounds.append(round_matches)
        return round_matches

    def generate_next_round_swiss(self) -> List[Match]:
        self.current_round_num += 1
        # Only pair players who are currently ACTIVE
        players = [p for p in self.get_standings() if p.active]
        
        paired = [False] * len(players)
        matches = []

        # 1. Handle BYE
        if len(players) % 2 != 0:
            # Lowest player who hasn't had a bye
            for i in range(len(players)-1, -1, -1):
                if not players[i].bye_received:
                    m = Match(players[i], None, is_bye=True)
                    matches.append(m)
                    paired[i] = True
                    break

        # 2. Backtracking Pairing
        def backtrack(idx):
            if idx >= len(players): return True
            if paired[idx]: return backtrack(idx + 1)
            
            p1 = players[idx]
            for j in range(idx + 1, len(players)):
                if not paired[j]:
                    p2 = players[j]
                    if p2 not in p1.opponents:
                        # Color logic & FIDE 3-in-a-row rule
                        hist1 = p1.color_history[-2:] if len(p1.color_history) >= 2 else []
                        hist2 = p2.color_history[-2:] if len(p2.color_history) >= 2 else []
                        
                        can_be_white1 = not (len(hist1) == 2 and hist1 == ['W', 'W'])
                        can_be_white2 = not (len(hist2) == 2 and hist2 == ['W', 'W'])
                        can_be_black1 = not (len(hist1) == 2 and hist1 == ['B', 'B'])
                        can_be_black2 = not (len(hist2) == 2 and hist2 == ['B', 'B'])

                        diff1 = p1.color_history.count('W') - p1.color_history.count('B')
                        diff2 = p2.color_history.count('W') - p2.color_history.count('B')
                        
                        # Attempt to assign p1 as White
                        if can_be_white1 and can_be_black2 and (diff1 <= diff2):
                            m = Match(p1, p2)
                        elif can_be_white2 and can_be_black1:
                            m = Match(p2, p1)
                        else:
                            continue # Constraint violation: 3 in a row
                            
                        matches.append(m)
                        paired[idx] = paired[j] = True
                        if backtrack(idx + 1): return True
                        # Backtrack
                        paired[idx] = paired[j] = False
                        matches.pop()
            return False

        if self.current_round_num == 1:
            # Accelerated/Standard R1: Top vs Bottom
            unpaired_indices = [i for i, val in enumerate(paired) if not val]
            half = len(unpaired_indices) // 2
            for i in range(half):
                p1, p2 = players[unpaired_indices[i]], players[unpaired_indices[i+half]]
                m = Match(p1, p2) if i % 2 == 0 else Match(p2, p1)
                matches.append(m)
                paired[unpaired_indices[i]] = paired[unpaired_indices[i+half]] = True
        else:
            if not backtrack(0):
                # Desperation: Pair greedily ignore rematches if absolutely necessary
                for i in range(len(players)):
                    if not paired[i]:
                        for j in range(i+1, len(players)):
                            if not paired[j]:
                                matches.append(Match(players[i], players[j]))
                                paired[i] = paired[j] = True
                                break
        
        self.rounds.append(matches)
        return matches

    def save_to_file(self, filename: str):
        data = {
            "name": self.name,
            "type": self.t_type.value,
            "current_round_num": self.current_round_num,
            "players": [p.to_dict() for p in self.players],
            "rounds": [[m.to_dict() for m in r] for r in self.rounds]
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load_from_file(cls, filename: str):
        if not os.path.exists(filename):
            raise TournamentError(f"File {filename} not found.")
            
        with open(filename, 'r') as f:
            data = json.load(f)
            
        # 1. Recreate players
        players_map = {}
        players_list = []
        for p_data in data["players"]:
            p = Player.from_dict(p_data)
            players_map[p.id] = p
            players_list.append(p)
            
        # 2. Re-link opponents
        for p_data in data["players"]:
            p = players_map[p_data["id"]]
            p.opponents = [players_map[oid] for oid in p_data["opponent_ids"]]
            
        t_type = TournamentType(data.get("type", "Swiss"))
        t = cls(data["name"], players_list, t_type)
        t.current_round_num = data["current_round_num"]
        
        # 3. Recreate rounds and matches
        for r_data in data["rounds"]:
            round_matches = []
            for m_data in r_data:
                white = players_map.get(m_data["white_id"])
                black = players_map.get(m_data["black_id"])
                m = Match(white, black, m_data["is_bye"])
                if m_data["result"]:
                    m.result = Result(m_data["result"])
                round_matches.append(m)
            t.rounds.append(round_matches)
            
        return t

    def export_csv(self, filename: str):
        standings = self.get_standings()
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Position', 'Name', 'Score', 'Buchholz', 'Rating', 'RatingDiff'])
            for i, p in enumerate(standings, 1):
                writer.writerow([i, p.name, p.score, p.buchholz, p.rating, f"{p.rating_change:+.1f}"])
        print(f"Standings exported to {filename}")

    def export_html(self, filename: str):
        standings = self.get_standings()
        rows = ""
        for i, p in enumerate(standings, 1):
            color = "#4ade80" if p.rating_change > 0 else "#f87171" if p.rating_change < 0 else "inherit"
            rows += f"""
            <tr>
                <td>{i}</td>
                <td style="font-weight: bold;">{p.name}</td>
                <td>{p.score:.1f}</td>
                <td>{p.buchholz:.1f}</td>
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
            <h1>{self.name} - Standings</h1>
            <p>Type: {self.t_type.value} | Rounds: {self.current_round_num}</p>
            <table>
                <thead><tr><th>#</th><th>Player</th><th>Score</th><th>BH</th><th>Rating</th><th>Elo Δ</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </body>
        </html>"""
        with open(filename, 'w') as f:
            f.write(html)
        print(f"Standings exported to {filename}")

def print_standings(t: Tournament):
    print(f"\n{'Pos':<4} {'Name':<12} {'Score':<6} {'BH':<6} {'Elo Δ':<8} {'Rating':<6}")
    print("-" * 55)
    for i, p in enumerate(t.get_standings(), 1):
        status = "" if p.active else " (Withdrawn)"
        print(f"{i:<4} {p.name + status:<12} {p.score:<6.1f} {p.buchholz:<6.1f} {p.rating_change:<+8.1f} {p.rating:<6}")

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
            
            if ',' in entry:
                parts = entry.split(',')
                name, rating = parts[0].strip(), int(parts[1].strip() or "1500")
            else:
                name, rating = entry, 1500
                
            try:
                player_list.append(Player(name, rating))
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
        t.save_to_file(save_file)

    # Main Loop
    while True:
        print_standings(t)
        print(f"\nTournament: {t.name} ({t.t_type.value})")
        print(f"Current Round: {t.current_round_num}")
        print("Commands: [n]ext round, [a]dd player, [w]ithdraw, [e]xport, [s]ave, [q]uit")
        cmd = input("Choice: ").lower()
        
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
                try:
                    rating = int(input("Rating (default 1500): ") or "1500")
                except ValueError:
                    rating = 1500
                p = Player(name, rating)
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
            
        elif cmd == 'n':
            try:
                pairings = t.generate_next_round()
            except Exception as e:
                print(f"Error generating pairings: {e}")
                continue
                
            for i, m in enumerate(pairings, 1):
                if m.is_bye:
                    t.record_match_result(m, "1-0")
                    print(f"Match {i}: {m}")
                    continue
                    
                while True:
                    print(f"Match {i}: {m}")
                    res = input("  Enter result (1-0, 0-1, 1/2-1/2): ").strip()
                    try:
                        t.record_match_result(m, res)
                        break
                    except TournamentError as e:
                        print(f"  Error: {e}")
            t.save_to_file(save_file)

if __name__ == "__main__":
    main()
