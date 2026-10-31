"""
Select, activate, and expire events after completed moves.
"""

import random
from piece import WHITE, BLACK
from setting import EVENT_GAP, WARNING_TURNS, EVENT_DURATION

EVENT_NAMES = {
    "freeze": "FROZEN FRONT",
    "promotion": "BORROWED CROWN",
    "block": "FRACTURED GROUND",
    "meteor": "METEOR STRIKE",
    "peace": "SANCTUARY",
}
DESCRIPTIONS = {
    "freeze": "Up to two pieces per side cannot move or attack. Kings are immune.",
    "promotion": "One pawn per side moves and captures as a queen. Real promotions stay permanent.",
    "block": "Six separated empty squares block landing and sliding paths. Kings may enter; knights may jump over.",
    "meteor": "A 2 x 2 zone within ranks 3-6 is struck. All non-king pieces in the zone are destroyed.",
    "peace": "Pieces on ranks 4-5 cannot be captured by non-kings. Capturing out of the zone is allowed.",
}


class ChaosEvent:
    def __init__(self, kind, targets=None, squares=None, remaining=EVENT_DURATION):
        self.kind = kind
        self.name = EVENT_NAMES[kind]
        self.description = DESCRIPTIONS[kind]
        self.remaining = remaining

        # Create separate target containers for each event.
        self.targets = []
        if targets is not None:
            self.targets = list(targets)
        self.squares = set()
        if squares is not None:
            self.squares = set(squares)

    def snapshot(self):
        """Copy event data for repetition tracking."""
        return [self.kind, self.targets.copy(), sorted(self.squares), self.remaining]


class EventManager:
    def __init__(self, seed=None, enabled=True):
        # A seed reproduces the random event sequence.
        self.rng = random.Random(seed)
        self.enabled = enabled
        self.active = None          # Currently active event.
        self.upcoming = None        # Announced event awaiting activation.
        self.cooldown = EVENT_GAP    # Turns until the next event.
        self.last_kind = None

    def choose_kind(self, board):
        choices = list(EVENT_NAMES)
        if self.last_kind in choices:
            choices.remove(self.last_kind)

        has_pawn = False
        for square, piece in board.pieces():
            if piece.kind == "P":
                has_pawn = True
                break
        if not has_pawn and "promotion" in choices:
            choices.remove("promotion")
        return self.rng.choice(choices)

    def choose_piece_targets(self, board, kind):
        """Choose eligible piece IDs for each side."""
        count = 1
        if kind == "freeze":
            count = 2

        targets = []
        for color in (WHITE, BLACK):
            candidates = []
            for square, piece in board.pieces(color):
                if piece.kind == "K":
                    continue
                if kind == "promotion" and piece.kind != "P":
                    continue
                candidates.append(piece.uid)

            # Limit targets to the available pieces.
            number_to_choose = min(count, len(candidates))
            targets.extend(self.rng.sample(candidates, number_to_choose))
        return targets

    def far_from_selected(self, square, selected):
        """Reject squares touching any selected square."""
        for other in selected:
            row_distance = abs(square[0] - other[0])
            column_distance = abs(square[1] - other[1])
            if row_distance <= 1 and column_distance <= 1:
                return False
        return True

    def choose_block_squares(self, board):
        empty = []
        for row in range(8):
            for column in range(8):
                if board.at((row, column)) is None:
                    empty.append((row, column))

        # Squares with matching row and column parity cannot touch.
        # At least one parity group contains six empty squares in a normal game.
        largest_group = []
        for row_parity in (0, 1):
            for column_parity in (0, 1):
                group = []
                for square in empty:
                    if square[0] % 2 == row_parity and square[1] % 2 == column_parity:
                        group.append(square)
                if len(group) > len(largest_group):
                    largest_group = group
        best = self.rng.sample(largest_group, min(6, len(largest_group)))

        # Try up to 40 random arrangements.
        for attempt in range(40):
            self.rng.shuffle(empty)
            selected = []
            for square in empty:
                if self.far_from_selected(square, selected):
                    selected.append(square)
                if len(selected) == 6:
                    break
            if len(selected) > len(best):
                best = selected
            if len(best) == 6:
                break
        return set(best)

    def make_event(self, board, kind=None):
        """Choose forecast targets without changing the board."""
        if kind is None:
            kind = self.choose_kind(board)
        if kind not in EVENT_NAMES:
            raise ValueError("Unknown chaos event: " + str(kind))

        event = ChaosEvent(kind)
        if kind in ("freeze", "promotion"):
            event.targets = self.choose_piece_targets(board, kind)
        elif kind == "block":
            event.squares = self.choose_block_squares(board)
        elif kind == "meteor":
            # Row indices 2-5 correspond to ranks 6-3.
            # Keep the entire 2x2 area within these ranks.
            top_row = self.rng.randrange(2, 5)
            left_column = self.rng.randrange(7)
            for row_offset in (0, 1):
                for column_offset in (0, 1):
                    event.squares.add((top_row + row_offset, left_column + column_offset))
        else:
            for row in (3, 4):
                for column in range(8):
                    event.squares.add((row, column))
        return event

    def _activate(self, board, event):
        """Apply the announced event to the board."""
        if event.kind in ("freeze", "promotion"):
            valid_targets = []
            for uid in event.targets:
                found = board.find(uid)
                if found is None:
                    continue  # Skip targets captured during the forecast.
                square, piece = found
                if event.kind == "freeze" and piece.kind != "K":
                    piece.frozen = True
                    valid_targets.append(uid)
                elif event.kind == "promotion" and piece.kind == "P":
                    piece.temporary_queen = True
                    valid_targets.append(uid)
            event.targets = valid_targets

        elif event.kind == "block":
            empty_targets = set()
            for square in event.squares:
                if board.at(square) is None:
                    empty_targets.add(square)
            event.squares = empty_targets
            board.blocked = empty_targets.copy()

        elif event.kind == "peace":
            board.peace_rows = {3, 4}

        elif event.kind == "meteor":
            destroyed = 0
            for row, column in event.squares:
                piece = board.at((row, column))
                if piece is not None and piece.kind != "K":
                    board.grid[row][column] = None
                    destroyed += 1
            if destroyed > 0:
                board.halfmove_clock = 0
            return "Meteor struck: " + str(destroyed) + " piece(s) destroyed."

        return event.name.title() + " is active for 2 turns."

    def _expire(self, board):
        # Clear temporary effects when the active event ends.
        for square, piece in board.pieces():
            piece.frozen = False
            piece.temporary_queen = False
        board.blocked.clear()
        board.peace_rows.clear()
        self.active = None

    def tick(self, board):
        """Advance one turn and return event notifications."""
        if not self.enabled:
            return []

        # Reduce the active event duration.
        if self.active is not None:
            self.active.remaining -= 1
            if self.active.remaining == 0:
                name = self.active.name.title()
                self._expire(board)
                self.cooldown = EVENT_GAP
                return [name + " ended."]
            return []

        # Show the forecast during the last two clear turns.
        self.cooldown -= 1
        if self.cooldown == WARNING_TURNS:
            self.upcoming = self.make_event(board)
            return ["Forecast: " + self.upcoming.name.title() + " in 2 turns."]

        # Activate the announced event when the countdown reaches zero.
        if self.cooldown == 0:
            event = self.upcoming
            self.upcoming = None
            self.last_kind = event.kind
            message = self._activate(board, event)
            if event.kind == "meteor":
                self.cooldown = EVENT_GAP
            else:
                self.active = event
            return [message]
        return []

    def snapshot(self):
        active_state = None
        if self.active is not None:
            active_state = self.active.snapshot()
        upcoming_state = None
        if self.upcoming is not None:
            upcoming_state = self.upcoming.snapshot()
        return [self.enabled, self.cooldown, active_state, upcoming_state, self.last_kind]

