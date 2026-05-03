from typing import List, Optional
from models import Player, Match


def assign_colors(p1: Player, p2: Player) -> Optional[Match]:
    hist1 = p1.color_history[-2:] if len(p1.color_history) >= 2 else []
    hist2 = p2.color_history[-2:] if len(p2.color_history) >= 2 else []

    ww1 = len(hist1) == 2 and hist1 == ['W', 'W']
    ww2 = len(hist2) == 2 and hist2 == ['W', 'W']
    bb1 = len(hist1) == 2 and hist1 == ['B', 'B']
    bb2 = len(hist2) == 2 and hist2 == ['B', 'B']

    diff1 = p1.color_history.count('W') - p1.color_history.count('B')
    diff2 = p2.color_history.count('W') - p2.color_history.count('B')

    if not ww1 and not bb2 and diff1 <= diff2:
        return Match(p1, p2)
    elif not ww2 and not bb1:
        return Match(p2, p1)
    elif not ww1 and not bb2:
        return Match(p1, p2)
    elif not ww2 and not bb1:
        return Match(p2, p1)
    return None


def generate_swiss_round(players: List[Player], round_num: int) -> List[Match]:
    active = [p for p in players if p.active]

    paired = [False] * len(active)
    matches = []

    if len(active) % 2 != 0:
        assigned = False
        for i in range(len(active) - 1, -1, -1):
            if not active[i].bye_received:
                m = Match(active[i], None, is_bye=True)
                matches.append(m)
                paired[i] = True
                assigned = True
                break
        if not assigned:
            m = Match(active[-1], None, is_bye=True)
            matches.append(m)
            paired[-1] = True

    def backtrack(idx):
        if idx >= len(active):
            return True
        if paired[idx]:
            return backtrack(idx + 1)

        p1 = active[idx]
        for j in range(idx + 1, len(active)):
            if not paired[j]:
                p2 = active[j]
                if p2 not in p1.opponents:
                    m = assign_colors(p1, p2)
                    if m is None:
                        continue
                    matches.append(m)
                    paired[idx] = paired[j] = True
                    if backtrack(idx + 1):
                        return True
                    paired[idx] = paired[j] = False
                    matches.pop()
        return False

    if round_num == 1:
        unpaired_indices = [i for i, val in enumerate(paired) if not val]
        half = len(unpaired_indices) // 2
        for i in range(half):
            p1, p2 = active[unpaired_indices[i]], active[unpaired_indices[i + half]]
            m = assign_colors(p1, p2) or Match(p1, p2)
            matches.append(m)
            paired[unpaired_indices[i]] = paired[unpaired_indices[i + half]] = True
    else:
        if not backtrack(0):
            for i in range(len(active)):
                if not paired[i]:
                    for j in range(i + 1, len(active)):
                        if not paired[j]:
                            m = assign_colors(active[i], active[j]) or Match(active[i], active[j])
                            matches.append(m)
                            paired[i] = paired[j] = True
                            break

    return matches


def generate_round_robin_schedule(players: List[Player]) -> List[List[Match]]:
    n = len(players)
    temp = players[:]
    if n % 2 != 0:
        temp.append(None)
        n += 1

    all_rounds = []
    for r in range(n - 1):
        round_matches = []
        for i in range(n // 2):
            p1, p2 = temp[i], temp[n - 1 - i]
            if p1 and p2:
                m = Match(p1, p2) if (i + r) % 2 == 0 else Match(p2, p1)
                round_matches.append(m)
            elif p1 or p2:
                round_matches.append(Match(p1 or p2, None, is_bye=True))
        all_rounds.append(round_matches)
        temp = [temp[0]] + [temp[-1]] + temp[1:-1]
    return all_rounds
