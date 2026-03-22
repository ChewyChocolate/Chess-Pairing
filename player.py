import uuid
from typing import List, Dict, Any
from errors import TournamentError

class Player:
    MAX_NAME_LENGTH = 50
    
    def __init__(self, name: str) -> None:
        if not name:
            raise TournamentError("Player name cannot be empty.")
        if len(name) > self.MAX_NAME_LENGTH:
            raise TournamentError(f"Player name cannot exceed {self.MAX_NAME_LENGTH} characters.")
        
        self.id: str = str(uuid.uuid4())[:8]
        self.name: str = name
        self._rating: int = 1200
        self.score: float = 0.0
        self.opponents: List['Player'] = []
        self.match_results: List[float] = []
        self.color_history: List[str] = []
        self.bye_received: bool = False
        self.active: bool = True
        
        # Tie-break metrics
        self.buchholz: float = 0.0
        self.sonneborn_berger: float = 0.0

    @property
    def rating(self) -> int:
        return self._rating
    
    @rating.setter
    def rating(self, value: int) -> None:
        if not isinstance(value, int):
            raise TournamentError("Rating must be an integer.")
        if value < 0 or value > 3000:
            raise TournamentError("Rating must be between 0 and 3000.")
        self._rating = value

    def __repr__(self) -> str:
        return f"{self.name} ({self.score})"

    def update_tiebreaks(self) -> None:
        """Calculates standard chess tie-breaks."""
        self.buchholz = sum(opp.score for opp in self.opponents)
        self.sonneborn_berger = sum(opp.score * res for opp, res in zip(self.opponents, self.match_results))

    def to_dict(self) -> Dict[str, Any]:
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
    def from_dict(cls, data: Dict[str, Any]) -> 'Player':
        p = cls(data["name"])
        p.id = data["id"]
        p._rating = data.get("rating", 1200)
        p.score = data["score"]
        p.match_results = data.get("match_results", [])
        p.color_history = data["color_history"]
        p.bye_received = data["bye_received"]
        p.active = data.get("active", True)
        return p
