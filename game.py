"""
Manage player input, turns, events, and game results.
"""

from board import Board
from events import EventManager
from piece import WHITE, BLACK, opponent, square_name
from rules import legal_moves, in_check, insufficient_material


class Game:
    def __init__(self, seed=None, chaos=True):
        self.board = Board()
        self.turn = WHITE
        self.ply = 0                 # Completed player turns.
        self.events = EventManager(seed, enabled=chaos)
        self.selected = None         # Selected square, or None.
        self.pending_promotion = []  # Promotion choices awaiting input.
        self.result = None
        self.message = "White to move. Select a piece to see legal moves."
        self.history = []
        self.position_history = []
        self.moves = []
        self.refresh_moves()
        self.record_position()

    def refresh_moves(self):
        """Recalculate legal moves for the current player."""
        self.moves = legal_moves(self.board, self.turn)

    def selected_moves(self):
        result = []
        for move in self.moves:
            if move.start == self.selected:
                result.append(move)
        return result

    def click_square(self, square):
        """Handle a board click without advancing invalid moves."""
        if self.result is not None or self.pending_promotion:
            return

        if square == self.selected:
            self.selected = None
            return

        # Check whether the clicked square is a legal destination.
        if self.selected is not None:
            candidates = []
            for move in self.selected_moves():
                if move.end == square:
                    candidates.append(move)
            if candidates:
                if candidates[0].promotion is not None:
                    self.pending_promotion = candidates
                    self.message = "Choose a piece for the pawn's permanent promotion."
                else:
                    self.play(candidates[0])
                return

        # Switch selection to another friendly piece.
        piece = self.board.at(square)
        if piece is None or piece.color != self.turn:
            self.message = "Illegal destination. Your turn has not been used."
        elif piece.frozen:
            self.selected = None
            self.message = "This piece is frozen: it cannot move or attack."
        else:
            self.selected = square
            destinations = set()
            for move in self.selected_moves():
                destinations.add(move.end)
            count = len(destinations)
            self.message = square_name(square) + ": " + str(count) + " legal destination(s)."

    def choose_promotion(self, kind):
        for move in self.pending_promotion:
            if move.promotion == kind:
                self.play(move)
                return

    def cancel_selection(self):
        self.selected = None
        self.pending_promotion = []
        self.message = "Selection cancelled."

    def play(self, move):
        """Validate and complete one turn."""
        if self.result is not None:
            raise ValueError("This game has already ended.")

        found = False
        for allowed_move in self.moves:
            if allowed_move.same_as(move):
                found = True
                break
        if not found:
            raise ValueError("That move is not legal in the current position.")

        # Apply the move, record it, and switch players.
        self.board.apply(move)
        self.ply += 1
        self.record_move(move)
        self.turn = opponent(self.turn)
        self.selected = None
        self.pending_promotion = []
        self.refresh_moves()

        # End the game if the move causes checkmate or stalemate.
        self.check_mate()
        if self.result is not None:
            self.message = self.result
            return

        # Apply events and recheck legal moves and results.
        notifications = self.events.tick(self.board)
        self.refresh_moves()
        self.record_position()
        self.check_mate()
        self.check_other_king()
        if self.result is None:
            self.check_automatic_draw()

        # Update the latest game message.
        if self.result is not None:
            self.message = self.result
        elif notifications:
            self.message = " ".join(notifications)
        else:
            self.message = self.turn.title() + " to move."
        self.history.extend(notifications)

    def record_move(self, move):
        notation = square_name(move.start) + " - " + square_name(move.end)
        if move.promotion is not None:
            notation += " = " + move.promotion
        self.history.append(str(self.ply) + ". " + self.turn.title() + " " + notation)

    def check_mate(self):
        """Detect checkmate or stalemate when no legal moves remain."""
        if len(self.moves) > 0:
            return
        if in_check(self.board, self.turn):
            self.result = opponent(self.turn).title() + " wins by checkmate."
        else:
            self.result = "Draw: stalemate."

    def check_other_king(self):
        """Check whether an event checkmated the other king."""
        other_color = opponent(self.turn)
        if not in_check(self.board, other_color):
            return
        if legal_moves(self.board, other_color):
            return

        if self.result is not None and in_check(self.board, self.turn):
            self.result = "Draw: both kings checkmated by the event."
        else:
            self.result = self.turn.title() + " wins by event checkmate."

    def check_automatic_draw(self):
        if insufficient_material(self.board, chaos=False):
            self.result = "Draw: insufficient material."
        elif self.board.halfmove_clock >= 150:
            self.result = "Draw: 75 moves without a pawn move or capture."
        elif self.position_history.count(self.position_snapshot()) >= 5:
            self.result = "Draw: fivefold repetition."

    # Track castling rights and repeated positions.
    def castling_rights(self):
        """Return castling rights based on king and rook movement."""
        rights = []
        for color in (WHITE, BLACK):
            row = 0
            if color == WHITE:
                row = 7
            king = self.board.at((row, 4))
            for column in (0, 7):
                rook = self.board.at((row, column))
                allowed = True
                if king is None or king.kind != "K" or king.color != color:
                    allowed = False
                elif king.moved:
                    allowed = False
                if rook is None or rook.kind != "R" or rook.color != color:
                    allowed = False
                elif rook.moved:
                    allowed = False
                rights.append(allowed)
        return rights

    def position_snapshot(self):
        """Record position and event data for repetition checks."""
        pieces = []
        for square, piece in self.board.pieces():
            starting_row = 1
            if piece.color == WHITE:
                starting_row = 6
            pawn_has_moved = False
            if piece.kind == "P" and square[0] == starting_row:
                pawn_has_moved = piece.moved
            pieces.append([square, piece.color, piece.kind, piece.frozen,
                           piece.temporary_queen, pawn_has_moved])

        # Include en passant only when a legal capture is available.
        en_passant = None
        for move in self.moves:
            if move.en_passant:
                en_passant = self.board.en_passant
                break

        event_state = None
        if self.events.enabled:
            event_state = self.events.snapshot()
        return [pieces, self.turn, self.castling_rights(), en_passant,
                sorted(self.board.blocked), sorted(self.board.peace_rows), event_state]

    def record_position(self):
        self.position_history.append(self.position_snapshot())

    def claim_draw(self):
        if self.result is not None or self.pending_promotion:
            return
        if self.board.halfmove_clock >= 100:
            self.result = "Draw claimed: 50-move rule."
        elif self.position_history.count(self.position_snapshot()) >= 3:
            self.result = "Draw claimed: threefold repetition."
        else:
            self.message = "No draw claim available (50 moves / threefold repetition)."
        if self.result is not None:
            self.message = self.result

