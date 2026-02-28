from enum import Enum
from typing import Optional
from player import Player

class Result(Enum):
    WHITE_WIN = "1-0"
    BLACK_WIN = "0-1"
    DRAW = "1/2-1/2"
    BYE = "1-0 (BYE)"

class Match:
    def __init__(self, white: Optional[Player], black: Optional[Player], is_bye: bool = False):
        self.white = white
        self.black = black
        self.is_bye = is_bye
        self.result: Optional[Result] = None
        self.timestamp: Optional[str] = None # When the result was set

    def to_dict(self):
        return {
            "white_id": self.white.id if self.white else None,
            "black_id": self.black.id if self.black else None,
            "is_bye": self.is_bye,
            "result": self.result.value if self.result else None,
            "timestamp": self.timestamp
        }

    def __repr__(self):
        if self.is_bye:
            p = self.white or self.black
            return f"{p.name} [BYE]"
        res_str = f" [{self.result.value}]" if self.result else ""
        return f"{self.white.name} (W) vs {self.black.name} (B){res_str}"
