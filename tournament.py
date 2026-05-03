import json
import os
import csv
import math
import logging
from datetime import datetime
from typing import List, Optional
from enum import Enum

from errors import TournamentError
from player import Player
from match import Match, Result
from pairing import generate_swiss_round, generate_round_robin_schedule

logger = logging.getLogger(__name__)

class TournamentType(Enum):
    SWISS = "Swiss"
    ROUND_ROBIN = "Round Robin"

class Tournament:
    MAX_NAME_LENGTH = 50
    MAX_SNAPSHOTS = 5
    
    def __init__(self, name: str, players: List[Player], t_type: TournamentType = TournamentType.SWISS,
                 total_rounds: Optional[int] = None):
        if not name:
            raise TournamentError("Tournament name cannot be empty.")
        if len(name) > self.MAX_NAME_LENGTH:
            raise TournamentError(f"Tournament name cannot exceed {self.MAX_NAME_LENGTH} characters.")
        
        self.name = name
        self.players = players
        self.t_type = t_type
        self.rounds: List[List[Match]] = []
        self.current_round_num = 0
        self._total_rounds = total_rounds

    def add_player(self, player: Player):
        self.players.append(player)
        if hasattr(self, '_rr_schedule'):
            delattr(self, '_rr_schedule')

    @property
    def total_rounds(self) -> int:
        if self.t_type == TournamentType.ROUND_ROBIN:
            n = len(self.players)
            return n - 1 if n % 2 == 0 else n
        if self._total_rounds is not None:
            return self._total_rounds
        # Default Swiss rounds: ceil(log2(n))
        return math.ceil(math.log2(len(self.players))) if self.players else 0

    @total_rounds.setter
    def total_rounds(self, value: int):
        self._total_rounds = value

    def get_standings(self) -> List[Player]:
        """Returns players sorted by score, then tie-breaks, then rating."""
        for p in self.players:
            p.update_tiebreaks()
        return sorted(self.players, 
                      key=lambda p: (p.score, p.sonneborn_berger, p.buchholz, p.rating), 
                      reverse=True)

    def record_match_result(self, match: Match, result_code: str):
        mapping = {
            "1-0": (Result.WHITE_WIN, 1.0, 0.0),
            "0-1": (Result.BLACK_WIN, 0.0, 1.0),
            "1/2-1/2": (Result.DRAW, 0.5, 0.5),
            "1-0 (BYE)": (Result.BYE, 1.0, 0.0)
        }

        if result_code not in mapping:
            raise TournamentError(f"Invalid result: {result_code}")

        res_enum, _, _ = mapping[result_code]
        match.result = res_enum
        match.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.recalculate_state()

    def recalculate_state(self):
        """Rebuilds all player states from the ground up based on match results."""
        for p in self.players:
            p.score = 0.0
            p.opponents = []
            p.match_results = []
            p.color_history = []
            p.bye_received = False

        for rnd in self.rounds:
            for match in rnd:
                if match.result is None:
                    continue
                
                if match.is_bye:
                    p = match.white or match.black
                    p.score += 1.0
                    p.bye_received = True
                else:
                    mapping = {
                        Result.WHITE_WIN: (1.0, 0.0, 'W', 'B'),
                        Result.BLACK_WIN: (0.0, 1.0, 'B', 'W'),
                        Result.DRAW: (0.5, 0.5, 'W', 'B')
                    }
                    if match.result in mapping:
                        w_pts, b_pts, w_col, b_col = mapping[match.result]
                        match.white.score += w_pts
                        match.black.score += b_pts
                        match.white.opponents.append(match.black)
                        match.black.opponents.append(match.white)
                        match.white.match_results.append(w_pts)
                        match.black.match_results.append(b_pts)
                        match.white.color_history.append(w_col)
                        match.black.color_history.append(b_col)

    def generate_next_round(self) -> List[Match]:
        if self.t_type == TournamentType.SWISS:
            return self.generate_next_round_swiss()
        else:
            return self.generate_next_round_round_robin()

    def generate_all_rounds_round_robin(self) -> List[List[Match]]:
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
            self._rr_schedule = self.generate_all_rounds_round_robin()
            
        if self.current_round_num >= len(self._rr_schedule):
            raise TournamentError("All Round Robin rounds completed.")
            
        round_matches = self._rr_schedule[self.current_round_num]
        self.current_round_num += 1
        self.rounds.append(round_matches)
        return round_matches

    def delete_last_round(self):
        """Removes the last generated round (the Panic button)."""
        if not self.rounds:
            raise TournamentError("No rounds to delete.")
            
        self.rounds.pop()
        self.current_round_num -= 1
        self.recalculate_state()

    def generate_next_round_swiss(self) -> List[Match]:
        self.current_round_num += 1
        players = [p for p in self.get_standings() if p.active]
        matches = generate_swiss_round(players, self.current_round_num)
        self.rounds.append(matches)
        return matches

    def create_snapshot(self, base_filename: str):
        """Creates a timestamped and round-based backup file with rotation."""
        base = os.path.splitext(base_filename)[0]
        round_num = len(self.rounds)
        snapshot_name = f"{base}_r{round_num}_backup.json"
        
        self.save_to_file(snapshot_name)
        
        # Rotate old snapshots - keep only last N
        dir_path = os.path.dirname(base_filename) or "."
        base_name = os.path.basename(base)
        
        old_snapshots = []
        for f in os.listdir(dir_path):
            if f.startswith(f"{base_name}_r") and f.endswith("_backup.json"):
                old_snapshots.append(os.path.join(dir_path, f))
        
        # Sort by modification time, oldest first
        old_snapshots.sort(key=lambda f: os.path.getmtime(f))
        
        # Remove oldest if exceeding max
        while len(old_snapshots) >= self.MAX_SNAPSHOTS:
            oldest = old_snapshots.pop(0)
            os.remove(oldest)
            logger.info(f"Removed old snapshot: {oldest}")
        
        logger.info(f"Snapshot created: {snapshot_name}")

    def save_to_file(self, filename: str):
        data = {
            "name": self.name,
            "type": self.t_type.value,
            "current_round_num": self.current_round_num,
            "total_rounds": self._total_rounds,
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
        total_rounds = data.get("total_rounds")
        t = cls(data["name"], players_list, t_type, total_rounds=total_rounds)
        t.current_round_num = data["current_round_num"]
        
        # 3. Recreate rounds and matches
        for r_data in data["rounds"]:
            round_matches = []
            for m_data in r_data:
                white = players_map.get(m_data["white_id"])
                black = players_map.get(m_data["black_id"])
                m = Match(white, black, m_data["is_bye"])
                if m_data.get("result"):
                    m.result = Result(m_data["result"])
                    m.timestamp = m_data.get("timestamp")
                round_matches.append(m)
            t.rounds.append(round_matches)
            
        return t

    def export_csv(self, filename: str):
        standings = self.get_standings()
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Position', 'Name', 'Score', 'SB', 'BH'])
            for i, p in enumerate(standings, 1):
                writer.writerow([i, p.name, p.score, f"{p.sonneborn_berger:.2f}",
                                 f"{p.buchholz:.2f}"])
        logger.info(f"Standings exported to {filename}")

    def export_html(self, filename: str):
        standings = self.get_standings()
        rows = ""
        for i, p in enumerate(standings, 1):
            rows += f"""
            <tr>
                <td>{i}</td>
                <td style="font-weight: bold;">{p.name}</td>
                <td>{p.score:.1f}</td>
                <td>{p.sonneborn_berger:.2f}</td>
                <td>{p.buchholz:.1f}</td>
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
            <p>Type: {self.t_type.value} | Rounds: {self.current_round_num}/{self.total_rounds}</p>
            <table>
                <thead><tr><th>#</th><th>Player</th><th>Score</th><th>SB</th><th>BH</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </body>
        </html>"""
        with open(filename, 'w') as f:
            f.write(html)
        logger.info(f"Standings exported to {filename}")
    def swap_players(self, round_idx: int, p1: Player, p2: Player):
        """Swaps two specific players within a round, regardless of board/side."""
        if round_idx >= len(self.rounds): return
        
        match1, side1 = None, ""
        match2, side2 = None, ""
        
        for m in self.rounds[round_idx]:
            if m.white == p1: match1, side1 = m, "white"
            elif m.black == p1: match1, side1 = m, "black"
            
            if m.white == p2: match2, side2 = m, "white"
            elif m.black == p2: match2, side2 = m, "black"
            
        if match1 and match2:
            setattr(match1, side1, p2)
            setattr(match2, side2, p1)
            self.recalculate_state()
