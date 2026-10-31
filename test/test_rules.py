"""Test movement, invalid moves, and special chess rules."""

import unittest
from board import Board
from piece import WHITE, BLACK, Move
from rules import legal_moves, attacked, in_check, insufficient_material


def position(*pieces):
    board = Board(setup=False)
    for square, color, kind in pieces:
        board.add(square, color, kind)
    return board


def kings():
    return position(((7, 4), WHITE, "K"), ((0, 4), BLACK, "K"))


def destinations(moves):
    result = set()
    for move in moves:
        result.add(move.end)
    return result


def castles_in(moves):
    result = []
    for move in moves:
        if move.castle:
            result.append(move)
    return result


def en_passant_moves(moves):
    result = []
    for move in moves:
        if move.en_passant:
            result.append(move)
    return result


def count_opening_positions(depth):
    """Count opening positions through three turns using nested loops."""
    board = Board()
    count = 0
    for first_move in legal_moves(board, WHITE):
        after_white = board.clone()
        after_white.apply(first_move)
        replies = legal_moves(after_white, BLACK)
        if depth == 2:
            count += len(replies)
        else:
            for reply in replies:
                after_black = after_white.clone()
                after_black.apply(reply)
                count += len(legal_moves(after_black, WHITE))
    return count


class ChessRulesTests(unittest.TestCase):
    def test_start_position_has_20_moves(self):
        self.assertEqual(len(legal_moves(Board(), WHITE)), 20)

    def test_start_position_two_ply_has_400_positions(self):
        self.assertEqual(count_opening_positions(2), 400)

    def test_start_position_three_ply_has_8902_positions(self):
        self.assertEqual(count_opening_positions(3), 8902)

    def test_piece_cannot_jump_through_piece(self):
        self.assertEqual(legal_moves(Board(), WHITE, (7, 2)), [])

    def test_pawn_cannot_jump_over_block(self):
        board = Board()
        board.blocked.add((5, 4))
        self.assertEqual(legal_moves(board, WHITE, (6, 4)), [])

    def test_knight_can_jump_over_block_but_not_land_on_it(self):
        board = Board()
        board.blocked.update({(6, 1), (5, 0)})
        ends = destinations(legal_moves(board, WHITE, (7, 1)))
        self.assertEqual(ends, {(5, 2)})

    def test_pinned_rook_cannot_expose_king(self):
        board = kings()
        board.add((6, 4), WHITE, "R")
        board.add((1, 4), BLACK, "R")
        self.assertNotIn((6, 3), destinations(legal_moves(board, WHITE, (6, 4))))

    def test_kings_cannot_be_adjacent(self):
        board = position(((4, 4), WHITE, "K"), ((2, 4), BLACK, "K"))
        self.assertNotIn((3, 4), destinations(legal_moves(board, WHITE)))

    def test_king_is_never_captured(self):
        board = kings()
        board.add((1, 4), WHITE, "R")
        self.assertNotIn((0, 4), destinations(legal_moves(board, WHITE)))

    def test_castle_both_sides(self):
        board = kings()
        board.add((7, 0), WHITE, "R")
        board.add((7, 7), WHITE, "R")
        castles = castles_in(legal_moves(board, WHITE))
        self.assertEqual(destinations(castles), {(7, 2), (7, 6)})
        for move in castles:
            if move.end == (7, 6):
                board.apply(move)
                break
        self.assertEqual(board.at((7, 5)).kind, "R")
        self.assertTrue(board.at((7, 5)).moved)
        self.assertIsNone(board.at((7, 7)))

    def test_no_castling_through_attack(self):
        board = kings()
        board.add((7, 7), WHITE, "R")
        board.add((2, 5), BLACK, "R")
        self.assertFalse(castles_in(legal_moves(board, WHITE)))

    def test_no_castling_when_rook_is_frozen(self):
        board = kings()
        board.add((7, 7), WHITE, "R").frozen = True
        self.assertFalse(castles_in(legal_moves(board, WHITE)))

    def test_no_castling_when_rook_route_is_blocked(self):
        board = kings()
        board.add((7, 0), WHITE, "R")
        board.blocked.add((7, 1))
        self.assertFalse(castles_in(legal_moves(board, WHITE)))

    def test_returned_king_cannot_castle(self):
        board = kings()
        board.add((7, 7), WHITE, "R")
        board.apply(Move((7, 4), (7, 5)))
        board.apply(Move((7, 5), (7, 4)))
        self.assertFalse(castles_in(legal_moves(board, WHITE)))

    def test_en_passant_executes(self):
        board = kings()
        board.add((3, 4), WHITE, "P")
        board.add((1, 3), BLACK, "P")
        board.apply(Move((1, 3), (3, 3)))
        move = en_passant_moves(legal_moves(board, WHITE))[0]
        board.apply(move)
        self.assertIsNone(board.at((3, 3)))
        self.assertEqual(board.at((2, 3)).color, WHITE)

    def test_en_passant_expires_after_other_move(self):
        board = kings()
        board.add((3, 4), WHITE, "P")
        board.add((1, 3), BLACK, "P")
        board.apply(Move((1, 3), (3, 3)))
        board.apply(Move((7, 4), (7, 5)))
        self.assertIsNone(board.en_passant)

    def test_en_passant_cannot_expose_king(self):
        board = position(((3, 0), WHITE, "K"), ((0, 4), BLACK, "K"),
                         ((3, 4), WHITE, "P"), ((1, 3), BLACK, "P"),
                         ((3, 7), BLACK, "R"))
        board.apply(Move((1, 3), (3, 3)))
        self.assertFalse(en_passant_moves(legal_moves(board, WHITE)))

    def test_all_four_promotions(self):
        board = kings()
        board.add((1, 0), WHITE, "P")
        moves = legal_moves(board, WHITE, (1, 0))
        promotion_choices = set()
        for move in moves:
            promotion_choices.add(move.promotion)
        self.assertEqual(promotion_choices, {"Q", "R", "B", "N"})
        for move in moves:
            if move.promotion == "N":
                board.apply(move)
                break
        self.assertEqual(board.at((0, 0)).kind, "N")

    def test_frozen_piece_has_no_moves_or_attacks(self):
        board = kings()
        rook = board.add((5, 4), BLACK, "R")
        self.assertTrue(in_check(board, WHITE))
        rook.frozen = True
        self.assertFalse(in_check(board, WHITE))
        self.assertEqual(legal_moves(board, BLACK, (5, 4)), [])

    def test_frozen_piece_still_blocks_rays(self):
        board = kings()
        board.add((2, 4), BLACK, "R")
        board.add((5, 4), WHITE, "B").frozen = True
        self.assertFalse(in_check(board, WHITE))

    def test_peace_prevents_capture_into_zone(self):
        board = kings()
        board.add((5, 0), WHITE, "R")
        board.add((3, 0), BLACK, "N")
        board.peace_rows = {3, 4}
        self.assertNotIn((3, 0), destinations(legal_moves(board, WHITE)))

    def test_peace_allows_capture_out_of_zone(self):
        board = kings()
        board.add((3, 0), WHITE, "R")
        board.add((1, 0), BLACK, "N")
        board.peace_rows = {3, 4}
        self.assertIn((1, 0), destinations(legal_moves(board, WHITE)))

    def test_peace_does_not_protect_king(self):
        board = position(((4, 4), WHITE, "K"), ((0, 0), BLACK, "K"),
                         ((4, 0), BLACK, "R"))
        board.peace_rows = {3, 4}
        self.assertTrue(in_check(board, WHITE))

    def test_king_may_capture_in_peace_zone(self):
        board = position(((5, 4), WHITE, "K"), ((0, 0), BLACK, "K"),
                         ((4, 4), BLACK, "N"))
        board.peace_rows = {3, 4}
        self.assertIn((4, 4), destinations(legal_moves(board, WHITE)))

    def test_king_can_enter_blocked_square(self):
        board = kings()
        board.blocked.add((6, 4))
        self.assertIn((6, 4), destinations(legal_moves(board, WHITE)))

    def test_blocked_square_does_not_stop_enemy_king_attack(self):
        board = position(((4, 4), WHITE, "K"), ((2, 4), BLACK, "K"))
        board.blocked.add((3, 4))
        self.assertNotIn((3, 4), destinations(legal_moves(board, WHITE)))

    def test_insufficient_material(self):
        board = kings()
        self.assertTrue(insufficient_material(board, chaos=False))
        board.add((5, 2), WHITE, "B")
        self.assertTrue(insufficient_material(board, chaos=False))
        board.add((5, 3), BLACK, "N")
        self.assertFalse(insufficient_material(board, chaos=False))


if __name__ == "__main__":
    unittest.main()
