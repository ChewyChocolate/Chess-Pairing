"""Unit tests for Chess Tournament Pairing System."""
import unittest
import os
import json
import tempfile
from player import Player
from tournament import Tournament, TournamentType
from match import Match, Result
from errors import TournamentError


class TestPlayer(unittest.TestCase):
    """Tests for Player class."""
    
    def test_create_player(self):
        p = Player("Test Player")
        self.assertEqual(p.name, "Test Player")
        self.assertEqual(p.score, 0.0)
        self.assertTrue(p.active)
    
    def test_empty_name_raises_error(self):
        with self.assertRaises(TournamentError):
            Player("")
    
    def test_name_too_long_raises_error(self):
        long_name = "A" * 51
        with self.assertRaises(TournamentError):
            Player(long_name)
    
    def test_tiebreak_calculation(self):
        p1 = Player("Player1")
        p2 = Player("Player2")
        p3 = Player("Player3")
        
        p1.opponents = [p2, p3]
        p1.match_results = [1.0, 0.5]  # Win + Draw
        p2.score = 2.0
        p3.score = 1.5
        
        p1.update_tiebreaks()
        
        # Buchholz = sum of opponent scores = 2.0 + 1.5 = 3.5
        self.assertEqual(p1.buchholz, 3.5)
        # SB = 2.0*1.0 + 1.5*0.5 = 2.0 + 0.75 = 2.75
        self.assertEqual(p1.sonneborn_berger, 2.75)
    
    def test_serialization(self):
        p = Player("Test")
        p.score = 3.5
        
        data = p.to_dict()
        self.assertEqual(data["name"], "Test")
        
        # Test deserialization
        p2 = Player.from_dict(data)
        self.assertEqual(p2.name, "Test")
        self.assertEqual(p2.score, 3.5)


class TestMatch(unittest.TestCase):
    """Tests for Match class."""
    
    def test_create_match(self):
        p1 = Player("White")
        p2 = Player("Black")
        m = Match(p1, p2)
        
        self.assertEqual(m.white, p1)
        self.assertEqual(m.black, p2)
        self.assertFalse(m.is_bye)
        self.assertIsNone(m.result)
    
    def test_bye_match(self):
        p = Player("Player")
        m = Match(p, None, is_bye=True)
        
        self.assertTrue(m.is_bye)
        self.assertEqual(m.white, p)
    
    def test_serialization(self):
        p1 = Player("White")
        p2 = Player("Black")
        m = Match(p1, p2)
        m.result = Result.WHITE_WIN
        
        data = m.to_dict()
        self.assertEqual(data["white_id"], p1.id)
        self.assertEqual(data["black_id"], p2.id)
        self.assertEqual(data["result"], "1-0")


class TestTournament(unittest.TestCase):
    """Tests for Tournament class."""
    
    def setUp(self):
        """Create test players and tournament."""
        self.players = [Player(f"Player{i}") for i in range(4)]
    
    def test_create_tournament(self):
        t = Tournament("Test", self.players, TournamentType.SWISS)
        
        self.assertEqual(t.name, "Test")
        self.assertEqual(len(t.players), 4)
        self.assertEqual(t.t_type, TournamentType.SWISS)
        self.assertEqual(t.current_round_num, 0)
    
    def test_empty_name_raises_error(self):
        with self.assertRaises(TournamentError):
            Tournament("", self.players)
    
    def test_name_too_long_raises_error(self):
        long_name = "A" * 51
        with self.assertRaises(TournamentError):
            Tournament(long_name, self.players)
    
    def test_swiss_rounds_auto_calculate(self):
        t = Tournament("Test", self.players, TournamentType.SWISS)
        # 4 players = ceil(log2(4)) = 2 rounds
        self.assertEqual(t.total_rounds, 2)
    
    def test_rr_rounds_auto_calculate(self):
        t = Tournament("Test", self.players, TournamentType.ROUND_ROBIN)
        # 4 players = 3 rounds
        self.assertEqual(t.total_rounds, 3)
    
    def test_generate_first_round_swiss(self):
        t = Tournament("Test", self.players, TournamentType.SWISS)
        matches = t.generate_next_round()
        
        self.assertEqual(t.current_round_num, 1)
        self.assertEqual(len(matches), 2)  # 4 players = 2 matches
        
        # Check no rematches
        for m in matches:
            self.assertNotIn(m.black, m.white.opponents)
    
    def test_generate_rr_schedule(self):
        t = Tournament("Test", self.players, TournamentType.ROUND_ROBIN)
        
        # Generate all rounds
        for _ in range(3):
            t.generate_next_round()
        
        # Should have 3 rounds
        self.assertEqual(len(t.rounds), 3)
        
        # Record results for all matches
        for rnd in t.rounds:
            for m in rnd:
                if not m.is_bye:
                    t.record_match_result(m, "1-0")
        
        # Each player should play each other once
        for p in self.players:
            self.assertEqual(len(p.opponents), 3)
    
    def test_record_match_result(self):
        t = Tournament("Test", self.players, TournamentType.SWISS)
        matches = t.generate_next_round()
        
        m = matches[0]
        t.record_match_result(m, "1-0")
        
        self.assertEqual(m.result, Result.WHITE_WIN)
        self.assertEqual(m.white.score, 1.0)
        self.assertEqual(m.black.score, 0.0)
    
    def test_bye_handling(self):
        # 3 players - odd number
        players = [Player(f"P{i}") for i in range(3)]
        t = Tournament("Test", players, TournamentType.SWISS)
        
        matches = t.generate_next_round()
        
        # Should have 1 match + 1 bye
        self.assertEqual(len(matches), 2)
        
        bye_match = [m for m in matches if m.is_bye][0]
        self.assertIsNotNone(bye_match)
        
        # Record the bye result
        t.record_match_result(bye_match, "1-0 (BYE)")
        self.assertEqual(bye_match.white.score, 1.0)  # Bye = 1 point
    
    def test_standings_sorting(self):
        t = Tournament("Test", self.players, TournamentType.SWISS)
        t.generate_next_round()
        
        # Record results: P1 beats P2, P3 beats P4
        t.rounds[0][0].result = Result.WHITE_WIN
        t.rounds[0][1].result = Result.WHITE_WIN
        t.recalculate_state()
        
        standings = t.get_standings()
        
        # First two should have 1.0, last two 0.0
        self.assertEqual(standings[0].score, 1.0)
        self.assertEqual(standings[1].score, 1.0)
        self.assertEqual(standings[2].score, 0.0)
        self.assertEqual(standings[3].score, 0.0)
    
    def test_save_and_load(self):
        t = Tournament("Test", self.players, TournamentType.SWISS)
        t.generate_next_round()
        t.rounds[0][0].result = Result.WHITE_WIN
        t.recalculate_state()
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            t.save_to_file(temp_file)
            
            # Load into new tournament
            t2 = Tournament.load_from_file(temp_file)
            
            self.assertEqual(t2.name, "Test")
            self.assertEqual(len(t2.players), 4)
            self.assertEqual(t2.current_round_num, 1)
            self.assertEqual(t2.rounds[0][0].result, Result.WHITE_WIN)
        finally:
            os.unlink(temp_file)
    
    def test_delete_last_round(self):
        t = Tournament("Test", self.players, TournamentType.SWISS)
        t.generate_next_round()
        
        self.assertEqual(t.current_round_num, 1)
        
        t.delete_last_round()
        
        self.assertEqual(t.current_round_num, 0)
        self.assertEqual(len(t.rounds), 0)
    
    def test_add_player(self):
        t = Tournament("Test", self.players, TournamentType.SWISS)
        new_player = Player("NewPlayer")
        
        t.add_player(new_player)
        
        self.assertEqual(len(t.players), 5)
        self.assertIn(new_player, t.players)


class TestSwissPairing(unittest.TestCase):
    """Tests for Swiss system pairing logic."""
    
    def test_no_rematches(self):
        """Ensure no player faces same opponent twice."""
        players = [Player(f"P{i}") for i in range(6)]
        t = Tournament("Test", players, TournamentType.SWISS, total_rounds=3)
        
        for _ in range(3):
            t.generate_next_round()
        
        for p in players:
            opponents = set(p.opponents)
            self.assertEqual(len(opponents), len(p.opponents))  # No duplicates
    
    def test_color_balance(self):
        """Test that colors are reasonably balanced."""
        players = [Player(f"P{i}") for i in range(4)]
        t = Tournament("Test", players, TournamentType.SWISS, total_rounds=3)
        
        for _ in range(3):
            t.generate_next_round()
        
        for p in players:
            white_count = p.color_history.count('W')
            black_count = p.color_history.count('B')
            # Should be close to balanced
            self.assertLessEqual(abs(white_count - black_count), 2)


if __name__ == "__main__":
    unittest.main()