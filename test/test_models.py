"""Test independent board copies and move comparisons."""

import unittest
from board import Board
from piece import Move


class ModelTests(unittest.TestCase):
    def test_trial_board_does_not_change_original(self):
        board = Board()
        board.at((6, 4)).frozen = True
        board.blocked.add((3, 0))
        trial = board.clone()

        trial.at((6, 4)).frozen = False
        trial.blocked.clear()
        trial.apply(Move((6, 4), (4, 4)))

        self.assertTrue(board.at((6, 4)).frozen)
        self.assertFalse(board.at((6, 4)).moved)
        self.assertIsNone(board.at((4, 4)))
        self.assertEqual(board.blocked, {(3, 0)})
        self.assertIsNone(board.en_passant)

    def test_clone_keeps_temporary_piece_state(self):
        board = Board()
        pawn = board.at((6, 4))
        pawn.temporary_queen = True
        pawn.moved = True
        copied_pawn = board.clone().at((6, 4))
        self.assertEqual(copied_pawn.uid, pawn.uid)
        self.assertEqual(copied_pawn.movement_kind(), "Q")
        self.assertTrue(copied_pawn.moved)
        self.assertIsNot(copied_pawn, pawn)

    def test_move_comparison_includes_special_rules(self):
        ordinary = Move((7, 4), (7, 6))
        castle = Move((7, 4), (7, 6), castle=True)
        self.assertTrue(ordinary.same_as(Move((7, 4), (7, 6))))
        self.assertFalse(ordinary.same_as(castle))
        self.assertFalse(ordinary.same_as(None))
        self.assertFalse(Move((1, 0), (0, 0), promotion="Q").same_as(
            Move((1, 0), (0, 0), promotion="N")))


if __name__ == "__main__":
    unittest.main()
