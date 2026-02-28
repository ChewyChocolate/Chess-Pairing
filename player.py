import uuid
from typing import List
from errors import TournamentError

class Player:
    def __init__(self, name: str):
        if not name:
            raise TournamentError("Player name cannot be empty.")
        
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.rating = 1200 # Default rating
        self.score = 0.0
        self.opponents: List['Player'] = []
        self.match_results: List[float] = []  # Points earned against each opponent in 'opponents'
        self.color_history: List[str] = []  # 'W' or 'B'
        self.bye_received = False
        self.active = True
        
        # Tie-break metrics
        self.buchholz = 0.0
        self.sonneborn_berger = 0.0

    def __repr__(self):
        return f"{self.name} ({self.score})"

    def update_tiebreaks(self):
        """Calculates standard chess tie-breaks."""
        self.buchholz = sum(opp.score for opp in self.opponents)
        
        # Sonneborn-Berger: Sum of scores of opponents you beat + 1/2 of those you drew
        self.sonneborn_berger = sum(opp.score * res for opp, res in zip(self.opponents, self.match_results))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "rating": self.rating,
            "score": self.score,
            "opponent_ids": [opp.id for opp in self.opponents],
            "match_results": self.match_results,
            "color_history": self.color_history,
            "bye_received": self.bye_received,
            "active": self.active
        }

    @classmethod
    def from_dict(cls, data):
        p = cls(data["name"])
        p.id = data["id"]
        p.rating = data.get("rating", 1200)
        p.score = data["score"]
        p.match_results = data.get("match_results", [])
        p.color_history = data["color_history"]
        p.bye_received = data["bye_received"]
        p.active = data.get("active", True)
        return p
