"""Unit tests for pairing module."""
import unittest
from player import Player
from match import Match
from pairing import assign_colors, generate_swiss_round, generate_round_robin_schedule


class TestAssignColors(unittest.TestCase):
    """Tests for assign_colors function."""

    def test_no_history_balanced(self):
        p1 = Player("A")
        p2 = Player("B")
        m = assign_colors(p1, p2)
        self.assertIsNotNone(m)
        # Higher-rated (default 1200 both) — first player should get white
        self.assertIn(m.white, (p1, p2))
        self.assertIn(m.black, (p1, p2))
        self.assertIsNot(m.white, m.black)

    def test_prevents_three_whites_in_a_row(self):
        p1 = Player("A")
        p2 = Player("B")
        p1.color_history = ['W', 'W']
        p2.color_history = ['B', 'B']
        m = assign_colors(p1, p2)
        self.assertIsNotNone(m)
        self.assertEqual(m.black, p1)  # p1 can't play white again

    def test_prevents_three_blacks_in_a_row(self):
        p1 = Player("A")
        p2 = Player("B")
        p1.color_history = ['B', 'B']
        p2.color_history = ['W', 'W']
        m = assign_colors(p1, p2)
        self.assertIsNotNone(m)
        self.assertEqual(m.white, p1)  # p1 can't play black again

    def test_both_restricted_returns_none(self):
        p1 = Player("A")
        p2 = Player("B")
        p1.color_history = ['W', 'W']
        p2.color_history = ['W', 'W']
        m = assign_colors(p1, p2)
        self.assertIsNone(m)

    def test_balances_color_difference(self):
        p1 = Player("A")
        p2 = Player("B")
        p1.color_history = ['W', 'B', 'W']  # diff = +1
        p2.color_history = ['B', 'W', 'B']  # diff = -1
        m = assign_colors(p1, p2)
        self.assertIsNotNone(m)
        # p2 has smaller diff (more blacks) so p2 should get white
        self.assertEqual(m.white, p2)


class TestGenerateSwissRound(unittest.TestCase):
    """Tests for generate_swiss_round function."""

    def test_even_players(self):
        players = [Player(f"P{i}") for i in range(4)]
        matches = generate_swiss_round(players, 1)
        self.assertEqual(len(matches), 2)

    def test_odd_players_grants_bye(self):
        players = [Player(f"P{i}") for i in range(3)]
        matches = generate_swiss_round(players, 1)
        self.assertEqual(len(matches), 2)  # 1 match + 1 bye
        byes = [m for m in matches if m.is_bye]
        self.assertEqual(len(byes), 1)

    def test_no_rematches_in_single_round(self):
        players = [Player(f"P{i}") for i in range(6)]
        matches = generate_swiss_round(players, 1)
        for m in matches:
            if not m.is_bye:
                self.assertNotIn(m.black, m.white.opponents)

    def test_round_two_no_rematches(self):
        players = [Player(f"P{i}") for i in range(4)]
        # Simulate round 1: P0 vs P1, P2 vs P3
        players[0].opponents.append(players[1])
        players[1].opponents.append(players[0])
        players[2].opponents.append(players[3])
        players[3].opponents.append(players[2])
        players[0].color_history.append('W')
        players[1].color_history.append('B')
        players[2].color_history.append('W')
        players[3].color_history.append('B')

        matches = generate_swiss_round(players, 2)
        self.assertEqual(len(matches), 2)
        for m in matches:
            if not m.is_bye:
                self.assertNotIn(m.black, m.white.opponents)

    def test_bye_not_repeated(self):
        players = [Player(f"P{i}") for i in range(3)]
        players[2].bye_received = True  # P2 already had a bye
        matches = generate_swiss_round(players, 2)
        bye_match = next(m for m in matches if m.is_bye)
        self.assertIsNot(bye_match.white, players[2])


class TestRoundRobinSchedule(unittest.TestCase):
    """Tests for generate_round_robin_schedule function."""

    def test_even_players_produces_n_minus_1_rounds(self):
        players = [Player(f"P{i}") for i in range(4)]
        schedule = generate_round_robin_schedule(players)
        self.assertEqual(len(schedule), 3)

    def test_odd_players_produces_n_rounds(self):
        players = [Player(f"P{i}") for i in range(5)]
        schedule = generate_round_robin_schedule(players)
        self.assertEqual(len(schedule), 5)

    def test_everyone_plays_everyone_once(self):
        players = [Player(f"P{i}") for i in range(4)]
        schedule = generate_round_robin_schedule(players)
        played_pairs = set()
        for rnd in schedule:
            for m in rnd:
                if not m.is_bye:
                    a, b = m.white, m.black
                    played_pairs.add((a, b) if a.name < b.name else (b, a))
        expected = {(players[i], players[j])
                    for i in range(4) for j in range(i + 1, 4)}
        self.assertEqual(played_pairs, expected)

    def test_no_player_gets_two_byes(self):
        players = [Player(f"P{i}") for i in range(3)]
        schedule = generate_round_robin_schedule(players)
        bye_counts = {p: 0 for p in players}
        for rnd in schedule:
            for m in rnd:
                if m.is_bye:
                    bye_counts[m.white or m.black] += 1
        for count in bye_counts.values():
            self.assertLessEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
