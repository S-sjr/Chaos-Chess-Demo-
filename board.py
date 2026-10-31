"""
Store the board and apply validated moves.
"""

from piece import Piece, WHITE, BLACK, PROMOTIONS


class Board:
    def __init__(self, setup=True):
        # Store squares as grid[row][column], starting at the top left.
        # Create independent rows; None marks an empty square.
        self.grid = []
        for row in range(8):
            new_row = []
            for column in range(8):
                new_row.append(None)
            self.grid.append(new_row)

        self.en_passant = None       # Current en passant destination.
        self.halfmove_clock = 0      # Turns since the last pawn move or capture.
        self.last_move = None
        self.blocked = set()         # Blocked square coordinates.
        self.peace_rows = set()      # Protected row indices.
        self.next_id = 1

        if setup:
            back_row = "RNBQKBNR"
            for column in range(8):
                kind = back_row[column]
                self.add((0, column), BLACK, kind)
                self.add((1, column), BLACK, "P")
                self.add((6, column), WHITE, "P")
                self.add((7, column), WHITE, kind)

    def inside(self, square):
        row, column = square
        return 0 <= row < 8 and 0 <= column < 8

    def at(self, square):
        """Return the piece at a square, or None."""
        if not self.inside(square):
            return None
        row, column = square
        return self.grid[row][column]

    def add(self, square, color, kind):
        row, column = square
        piece = Piece(color, kind, self.next_id)
        self.next_id += 1
        self.grid[row][column] = piece
        return piece

    def pieces(self, color=None):
        """Return square-piece pairs, optionally filtered by color."""
        result = []
        for row in range(8):
            for column in range(8):
                piece = self.grid[row][column]
                if piece is None:
                    continue
                if color is not None and piece.color != color:
                    continue
                result.append(((row, column), piece))
        return result

    def find(self, uid):
        for square, piece in self.pieces():
            if piece.uid == uid:
                return square, piece
        return None

    def king(self, color):
        for square, piece in self.pieces(color):
            if piece.kind == "K":
                return square
        return None

    def clone(self):
        """Copy the board for move simulation."""
        new_board = Board(setup=False)
        for square, piece in self.pieces():
            row, column = square
            new_board.grid[row][column] = piece.copy()

        # Copy coordinates directly and duplicate mutable sets.
        new_board.en_passant = self.en_passant
        new_board.halfmove_clock = self.halfmove_clock
        new_board.last_move = self.last_move  # Share the last move, which is only read after creation.
        new_board.blocked = self.blocked.copy()
        new_board.peace_rows = self.peace_rows.copy()
        new_board.next_id = self.next_id
        return new_board

    def apply(self, move):
        """Apply a validated move and return the captured piece."""
        piece = self.at(move.start)
        if piece is None:
            raise ValueError("There is no piece on the starting square.")
        if move.promotion is not None and move.promotion not in PROMOTIONS:
            raise ValueError("Choose queen, rook, bishop or knight.")

        captured = self.at(move.end)
        if captured is not None and captured.kind == "K":
            raise ValueError("Kings cannot be captured.")

        start_row, start_column = move.start
        end_row, end_column = move.end
        was_pawn = piece.kind == "P"
        used_pawn_moves = piece.movement_kind() == "P"

        # Remove the captured piece, including an adjacent en passant victim.
        self.grid[start_row][start_column] = None
        if move.en_passant:
            captured = self.grid[start_row][end_column]
            self.grid[start_row][end_column] = None

        # Move the rook during castling.
        if move.castle:
            if end_column == 6:
                rook_start = 7
                rook_end = 5
            else:
                rook_start = 0
                rook_end = 3
            rook = self.grid[start_row][rook_start]
            self.grid[start_row][rook_start] = None
            self.grid[start_row][rook_end] = rook
            rook.moved = True

        # Place the piece and mark it as moved.
        self.grid[end_row][end_column] = piece
        piece.moved = True

        # A normal two-square pawn move creates the next en passant target.
        self.en_passant = None
        if used_pawn_moves and abs(end_row - start_row) == 2:
            middle_row = (start_row + end_row) // 2
            self.en_passant = (middle_row, start_column)

        # Permanent promotion replaces the kind and clears the temporary boost.
        if was_pawn and end_row in (0, 7):
            if move.promotion is None:
                piece.kind = "Q"
            else:
                piece.kind = move.promotion
            piece.temporary_queen = False

        if was_pawn or captured is not None:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        self.last_move = move
        return captured

