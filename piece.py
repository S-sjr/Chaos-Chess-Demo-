"""
Store chess pieces and moves.
"""

WHITE = "white"
BLACK = "black"

# K: king, Q: queen, R: rook, B: bishop, N: knight, P: pawn.
KINDS = ("K", "Q", "R", "B", "N", "P")
PROMOTIONS = ("Q", "R", "B", "N")


def opponent(color):
    """Return the opposing color."""
    if color == WHITE:
        return BLACK
    return WHITE


class Piece:
    def __init__(self, color, kind, uid):
        self.color = color
        self.kind = kind
        # Keep the same ID when a piece moves.
        self.uid = uid
        self.moved = False
        self.frozen = False
        self.temporary_queen = False

    def movement_kind(self):
        """Return the movement kind, including temporary promotion."""
        if self.kind == "P" and self.temporary_queen:
            return "Q"
        return self.kind

    def copy(self):
        """Copy the piece and its current effects."""
        new_piece = Piece(self.color, self.kind, self.uid)
        new_piece.moved = self.moved
        new_piece.frozen = self.frozen
        new_piece.temporary_queen = self.temporary_queen
        return new_piece


class Move:
    """Store a move and its special actions."""

    def __init__(self, start, end, promotion=None, castle=False, en_passant=False):
        self.start = start
        self.end = end
        self.promotion = promotion
        self.castle = castle
        self.en_passant = en_passant

    def same_as(self, other):
        """Compare the coordinates and special actions of two moves."""
        if not isinstance(other, Move):
            return False
        if self.start != other.start or self.end != other.end:
            return False
        if self.promotion != other.promotion:
            return False
        if self.castle != other.castle:
            return False
        if self.en_passant != other.en_passant:
            return False
        return True


def square_name(square):
    """Convert board coordinates to chess notation."""
    row, column = square
    letters = "abcdefgh"
    return letters[column] + str(8 - row)

