import uuid
from typing import List, Optional, Dict
from enum import Enum


class TournamentError(Exception):
    pass


class Result(Enum):
    WHITE_WIN = "1-0"
    BLACK_WIN = "0-1"
    DRAW = "1/2-1/2"
    BYE = "1-0 (BYE)"


class TournamentType(Enum):
    SWISS = "Swiss"
    ROUND_ROBIN = "Round Robin"


class Player:
    def __init__(self, name: str, rating: int = 1500):
        if not name:
            raise TournamentError("Player name cannot be empty.")
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.rating = rating
        self.score = 0.0
        self.opponents: List['Player'] = []
        self.color_history: List[str] = []
        self.bye_received = False
        self.active = True
        self.rating_change = 0.0
        self.buchholz = 0.0
        self.sonneborn_berger = 0.0
        self.opponent_results: Dict[str, float] = {}

    def __repr__(self):
        return f"{self.name} ({self.score})"

    def update_tiebreaks(self):
        self.buchholz = sum(opp.score for opp in self.opponents)
        sb = 0.0
        for opp_id, pts in self.opponent_results.items():
            for opp in self.opponents:
                if opp.id == opp_id:
                    if pts == 1.0:
                        sb += opp.score
                    elif pts == 0.5:
                        sb += opp.score * 0.5
                    break
        self.sonneborn_berger = sb

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "rating": self.rating,
            "score": self.score,
            "opponent_ids": [opp.id for opp in self.opponents],
            "opponent_results": self.opponent_results,
            "color_history": self.color_history,
            "bye_received": self.bye_received,
            "active": self.active,
            "rating_change": self.rating_change,
            "buchholz": self.buchholz,
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
        p.buchholz = data.get("buchholz", 0.0)
        p.opponent_results = data.get("opponent_results", {})
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
            "result": self.result.value if self.result else None,
        }

    def __repr__(self):
        if self.is_bye:
            p = self.white or self.black
            return f"{p.name} [BYE]"
        white_name = self.white.name if self.white else "?"
        black_name = self.black.name if self.black else "?"
        res_str = f" [{self.result.value}]" if self.result else ""
        return f"{white_name} (W) vs {black_name} (B){res_str}"
