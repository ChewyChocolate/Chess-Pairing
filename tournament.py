from typing import List, Optional
from models import Player, Match, Result, TournamentType, TournamentError
from pairing import generate_swiss_round, generate_round_robin_schedule


class Tournament:
    def __init__(self, name: str, players: List[Player],
                 t_type: TournamentType = TournamentType.SWISS,
                 k: int = 32):
        self.name = name
        self.players = players
        self.t_type = t_type
        self.rounds: List[List[Match]] = []
        self.current_round_num = 0
        self.k = k
        self._rr_schedule: Optional[List[List[Match]]] = None

    def add_player(self, player: Player):
        self.players.append(player)

    def get_standings(self) -> List[Player]:
        for p in self.players:
            p.update_tiebreaks()
        return sorted(self.players, key=lambda p: (p.score, p.buchholz, p.sonneborn_berger, p.rating), reverse=True)

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
            "1/2-1/2": (Result.DRAW, 0.5, 0.5),
        }

        if result_code not in mapping:
            raise TournamentError(f"Invalid result: {result_code}")

        res_enum, w_pts, b_pts = mapping[result_code]
        match.result = res_enum

        match._undo_data = {
            'white': {
                'score': match.white.score,
                'rating': match.white.rating,
                'rating_change': match.white.rating_change,
                'opponents': list(match.white.opponents),
                'color_history': list(match.white.color_history),
                'opponent_results': dict(match.white.opponent_results),
            },
            'black': {
                'score': match.black.score,
                'rating': match.black.rating,
                'rating_change': match.black.rating_change,
                'opponents': list(match.black.opponents),
                'color_history': list(match.black.color_history),
                'opponent_results': dict(match.black.opponent_results),
            }
        }

        expected_w = 1 / (1 + 10 ** ((match.black.rating - match.white.rating) / 400))
        expected_b = 1 - expected_w

        diff_w = self.k * (w_pts - expected_w)
        diff_b = self.k * (b_pts - expected_b)

        match.white.rating_change += diff_w
        match.black.rating_change += diff_b
        match.white.rating += diff_w
        match.black.rating += diff_b

        match.white.score += w_pts
        match.black.score += b_pts

        match.white.opponents.append(match.black)
        match.black.opponents.append(match.white)
        match.white.color_history.append('W')
        match.black.color_history.append('B')

        match.white.opponent_results[match.black.id] = w_pts
        match.black.opponent_results[match.white.id] = b_pts

    def undo_last_match(self) -> Optional[Match]:
        if not self.rounds:
            return None
        round_matches = self.rounds[-1]
        for i in range(len(round_matches) - 1, -1, -1):
            match = round_matches[i]
            if match.result is not None:
                undo = getattr(match, '_undo_data', None)
                if undo is None:
                    return None
                for side in ('white', 'black'):
                    p = getattr(match, side)
                    if p is None:
                        continue
                    data = undo[side]
                    p.score = data['score']
                    p.rating = data['rating']
                    p.rating_change = data['rating_change']
                    p.opponents = data['opponents']
                    p.color_history = data['color_history']
                    p.opponent_results = data['opponent_results']
                match.result = None
                return match
        return None

    def undo_last_round(self) -> bool:
        if not self.rounds:
            return False
        count = 0
        while self.undo_last_match() is not None:
            count += 1
        self.rounds.pop()
        self.current_round_num -= 1
        return count > 0

    def generate_next_round(self) -> List[Match]:
        if self.t_type == TournamentType.SWISS:
            matches = generate_swiss_round(self.get_standings(), self.current_round_num + 1)
            self.current_round_num += 1
            self.rounds.append(matches)
            return matches
        else:
            if self._rr_schedule is None:
                self._rr_schedule = generate_round_robin_schedule(self.players)
            if self.current_round_num >= len(self._rr_schedule):
                raise TournamentError("All Round Robin rounds completed.")
            round_matches = self._rr_schedule[self.current_round_num]
            self.current_round_num += 1
            self.rounds.append(round_matches)
            return round_matches

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.t_type.value,
            "current_round_num": self.current_round_num,
            "k": self.k,
            "players": [p.to_dict() for p in self.players],
            "rounds": [[m.to_dict() for m in r] for r in self.rounds],
        }

    @classmethod
    def from_dict(cls, data):
        players_map = {}
        players_list = []
        for p_data in data["players"]:
            p = Player.from_dict(p_data)
            players_map[p.id] = p
            players_list.append(p)

        for p_data in data["players"]:
            p = players_map[p_data["id"]]
            p.opponents = [players_map[oid] for oid in p_data["opponent_ids"]]

        t_type = TournamentType(data.get("type", "Swiss"))
        t = cls(data["name"], players_list, t_type, k=data.get("k", 32))
        t.current_round_num = data["current_round_num"]

        for r_data in data["rounds"]:
            round_matches = []
            for m_data in r_data:
                white = players_map.get(m_data["white_id"])
                black = players_map.get(m_data["black_id"])
                m = Match(white, black, m_data.get("is_bye", False))
                if m_data.get("result"):
                    m.result = Result(m_data["result"])
                round_matches.append(m)
            t.rounds.append(round_matches)

        return t
