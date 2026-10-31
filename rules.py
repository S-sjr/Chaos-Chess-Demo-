"""
Calculate attacks, legal moves, and draw conditions.
"""

from piece import Move, WHITE, PROMOTIONS, opponent

# Directions use (row change, column change).
STRAIGHT = ((-1, 0), (1, 0), (0, -1), (0, 1))
DIAGONAL = ((-1, -1), (-1, 1), (1, -1), (1, 1))
KNIGHT = ((-2, -1), (-2, 1), (-1, -2), (-1, 2),
          (1, -2), (1, 2), (2, -1), (2, 1))


def sliding_directions(kind):
    if kind == "R":
        return STRAIGHT
    if kind == "B":
        return DIAGONAL
    return STRAIGHT + DIAGONAL  # Queens move along ranks, files, and diagonals.


def attacked(board, square, by_color):
    """Return whether a side attacks the given square."""
    for start, piece in board.pieces(by_color):
        if piece.frozen:
            continue

        kind = piece.movement_kind()
        row_distance = square[0] - start[0]
        column_distance = square[1] - start[1]

        # Kings ignore blocked squares; other pieces cannot attack them.
        if kind == "K":
            if max(abs(row_distance), abs(column_distance)) == 1:
                return True
            continue

        if square in board.blocked:
            continue

        if kind == "P":
            direction = 1
            if by_color == WHITE:
                direction = -1
            if row_distance == direction and abs(column_distance) == 1:
                return True
        elif kind == "N":
            if (row_distance, column_distance) in KNIGHT:
                return True
        else:
            # Scan each ray until a piece or blocked square stops it.
            for row_step, column_step in sliding_directions(kind):
                row = start[0] + row_step
                column = start[1] + column_step
                while board.inside((row, column)):
                    current = (row, column)
                    if current in board.blocked:
                        break
                    if current == square:
                        return True
                    if board.at(current) is not None:
                        break
                    row += row_step
                    column += column_step
    return False


def in_check(board, color):
    king_square = board.king(color)
    if king_square is None:
        return False
    # Sanctuary does not protect kings.
    return attacked(board, king_square, opponent(color))


def can_capture(board, piece, square):
    """Check capture restrictions without checking the path or king safety."""
    target = board.at(square)
    if target is None:
        return False
    if target.color == piece.color:
        return False
    if target.kind == "K":
        return False
    if piece.kind != "K" and square[0] in board.peace_rows:
        return False
    return True


def moves_to(piece, start, end):
    """Create move options, including all permanent promotions."""
    moves = []
    if piece.kind == "P" and end[0] in (0, 7):
        for kind in PROMOTIONS:
            moves.append(Move(start, end, promotion=kind))
    else:
        moves.append(Move(start, end))
    return moves


def pawn_moves(board, start, piece):
    row, column = start
    direction = 1
    starting_row = 1
    if piece.color == WHITE:
        direction = -1
        starting_row = 6

    moves = []

    # Pawn advances require an empty, unblocked path.
    one_step = (row + direction, column)
    if board.inside(one_step):
        if board.at(one_step) is None and one_step not in board.blocked:
            moves.extend(moves_to(piece, start, one_step))
            two_steps = (row + 2 * direction, column)
            if row == starting_row and not piece.moved:
                if board.at(two_steps) is None and two_steps not in board.blocked:
                    moves.append(Move(start, two_steps))

    # Pawns capture one square diagonally forward.
    for column_step in (-1, 1):
        end = (row + direction, column + column_step)
        if not board.inside(end) or end in board.blocked:
            continue

        if can_capture(board, piece, end):
            moves.extend(moves_to(piece, start, end))
        elif end == board.en_passant and board.at(end) is None:
            victim_square = (row, column + column_step)
            victim = board.at(victim_square)
            if victim is None or victim.kind != "P":
                continue
            if victim.color == piece.color:
                continue
            # En passant cannot bypass sanctuary protection.
            if victim_square[0] in board.peace_rows or end[0] in board.peace_rows:
                continue
            moves.append(Move(start, end, en_passant=True))
    return moves


def short_moves(board, start, piece):
    """Generate king or knight moves."""
    directions = KNIGHT
    if piece.kind == "K":
        directions = STRAIGHT + DIAGONAL

    moves = []
    for row_step, column_step in directions:
        end = (start[0] + row_step, start[1] + column_step)
        if not board.inside(end):
            continue
        if piece.kind != "K" and end in board.blocked:
            continue
        if board.at(end) is None or can_capture(board, piece, end):
            moves.append(Move(start, end))
    return moves


def sliding_moves(board, start, piece):
    """Generate rook, bishop, or queen moves along clear rays."""
    moves = []
    for row_step, column_step in sliding_directions(piece.movement_kind()):
        row = start[0] + row_step
        column = start[1] + column_step
        while board.inside((row, column)):
            end = (row, column)
            if end in board.blocked:
                break
            if board.at(end) is None:
                moves.extend(moves_to(piece, start, end))
            else:
                if can_capture(board, piece, end):
                    moves.extend(moves_to(piece, start, end))
                break
            row += row_step
            column += column_step
    return moves


def castle_moves(board, start, king):
    """Generate castling candidates with a safe intermediate square."""
    row = 0
    if king.color == WHITE:
        row = 7
    if start != (row, 4) or king.moved:
        return []
    if in_check(board, king.color):
        return []

    moves = []
    for side in ("king_side", "queen_side"):
        if side == "king_side":
            rook_column = 7
            end_column = 6
            between_columns = (5, 6)
            transit_column = 5
        else:
            rook_column = 0
            end_column = 2
            between_columns = (1, 2, 3)
            transit_column = 3

        rook = board.at((row, rook_column))
        if rook is None or rook.kind != "R" or rook.color != king.color:
            continue
        if rook.moved or rook.frozen:
            continue

        path_is_clear = True
        for column in between_columns:
            square = (row, column)
            if board.at(square) is not None or square in board.blocked:
                path_is_clear = False
                break
        if not path_is_clear:
            continue

        # Check the king on the intermediate castling square.
        trial_board = board.clone()
        trial_board.apply(Move(start, (row, transit_column)))
        if not in_check(trial_board, king.color):
            moves.append(Move(start, (row, end_column), castle=True))
    return moves


def pseudo_moves(board, start):
    """Generate moves before checking king safety."""
    piece = board.at(start)
    if piece is None or piece.frozen:
        return []

    kind = piece.movement_kind()
    if kind == "P":
        return pawn_moves(board, start, piece)
    if kind == "K":
        moves = short_moves(board, start, piece)
        moves.extend(castle_moves(board, start, piece))
        return moves
    if kind == "N":
        return short_moves(board, start, piece)
    return sliding_moves(board, start, piece)


def legal_moves(board, color, start=None):
    """Simulate moves and keep those that leave the king safe."""
    positions = []
    if start is not None:
        positions.append(start)
    else:
        for square, piece in board.pieces(color):
            positions.append(square)

    result = []
    for square in positions:
        piece = board.at(square)
        if piece is None or piece.color != color:
            continue
        for move in pseudo_moves(board, square):
            trial_board = board.clone()
            trial_board.apply(move)
            if not in_check(trial_board, color):
                result.append(move)
    return result


def insufficient_material(board, chaos=True):
    """Detect common insufficient-material positions."""
    remaining = []
    for square, piece in board.pieces():
        if piece.kind != "K":
            remaining.append((square, piece))

    if len(remaining) == 0:
        return True
    if chaos:
        return False
    if len(remaining) == 1:
        square, piece = remaining[0]
        if piece.kind in ("B", "N"):
            return True

    # Bishops confined to one square color cannot force mate.
    first_square, first_piece = remaining[0]
    first_square_color = (first_square[0] + first_square[1]) % 2
    for square, piece in remaining:
        if piece.kind != "B":
            return False
        if (square[0] + square[1]) % 2 != first_square_color:
            return False
    return True

