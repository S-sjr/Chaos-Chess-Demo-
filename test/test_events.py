"""Event targeting, expiry and interactions with the board."""

import unittest
from board import Board
from events import EventManager, ChaosEvent
from piece import WHITE, BLACK, Move
from rules import in_check


class EventTests(unittest.TestCase):
    def test_forecast_and_two_turn_duration(self):
        board, manager = Board(), EventManager(seed=2)
        manager.tick(board)
        self.assertIsNone(manager.upcoming)
        manager.tick(board)
        self.assertIsNotNone(manager.upcoming)
        manager.upcoming = manager.make_event(board, "freeze")
        manager.tick(board)
        self.assertIsNone(manager.active)
        manager.tick(board)
        self.assertEqual(manager.active.remaining, 2)
        frozen_count = 0
        for square, piece in board.pieces():
            if piece.frozen:
                frozen_count += 1
        self.assertEqual(frozen_count, 4)
        manager.tick(board)
        self.assertEqual(manager.active.remaining, 1)
        manager.tick(board)
        self.assertIsNone(manager.active)
        for square, piece in board.pieces():
            self.assertFalse(piece.frozen)
        self.assertEqual(manager.cooldown, 4)
        self.assertIsNone(manager.upcoming)

    def test_freeze_selects_two_each_and_never_king(self):
        board, manager = Board(), EventManager(seed=1)
        event = manager.make_event(board, "freeze")
        white_count = 0
        black_count = 0
        for uid in event.targets:
            square, piece = board.find(uid)
            if piece.color == WHITE:
                white_count += 1
            else:
                black_count += 1
            self.assertNotEqual(piece.kind, "K")
        self.assertEqual(white_count, 2)
        self.assertEqual(black_count, 2)

    def test_fewer_than_two_non_kings(self):
        board = Board(False)
        board.add((7, 4), WHITE, "K")
        board.add((0, 4), BLACK, "K")
        board.add((6, 2), WHITE, "P")
        event = EventManager().make_event(board, "freeze")
        self.assertEqual(len(event.targets), 1)

    def test_blocks_are_six_empty_non_adjacent_squares(self):
        board = Board()
        for seed in range(30):
            event = EventManager(seed).make_event(board, "block")
            self.assertEqual(len(event.squares), 6)
            for sq in event.squares:
                self.assertIsNone(board.at(sq))
                for other in event.squares - {sq}:
                    self.assertGreater(max(abs(sq[0]-other[0]), abs(sq[1]-other[1])), 1)

    def test_occupied_preview_block_is_skipped(self):
        board, manager = Board(), EventManager()
        event = ChaosEvent("block", squares={(4, 4), (3, 2)})
        board.apply(Move((6, 4), (4, 4)))
        manager._activate(board, event)
        self.assertEqual(board.blocked, {(3, 2)})

    def test_piece_targets_follow_the_piece(self):
        board, manager = Board(), EventManager()
        pawn = board.at((6, 4))
        event = ChaosEvent("freeze", targets=[pawn.uid])
        board.apply(Move((6, 4), (4, 4)))
        manager._activate(board, event)
        self.assertTrue(board.at((4, 4)).frozen)

    def test_captured_preview_target_is_skipped(self):
        board, manager = Board(), EventManager()
        event = ChaosEvent("promotion", targets=[board.at((6, 4)).uid])
        board.grid[6][4] = None
        manager._activate(board, event)
        self.assertEqual(event.targets, [])

    def test_meteor_zone_is_two_by_two_in_ranks_3_to_6(self):
        for seed in range(30):
            event = EventManager(seed).make_event(Board(), "meteor")
            rows = set()
            cols = set()
            for row, column in event.squares:
                rows.add(row)
                cols.add(column)
            self.assertEqual(len(event.squares), 4)
            self.assertEqual(len(rows), 2)
            self.assertEqual(len(cols), 2)
            self.assertTrue(rows <= {2, 3, 4, 5})
            self.assertEqual(max(rows)-min(rows), 1)
            self.assertEqual(max(cols)-min(cols), 1)

    def test_meteor_kills_pieces_but_spares_king(self):
        board, manager = Board(False), EventManager()
        board.add((3, 3), WHITE, "K")
        board.add((3, 4), WHITE, "Q")
        board.add((4, 3), BLACK, "R")
        event = ChaosEvent("meteor", squares={(3, 3), (3, 4), (4, 3), (4, 4)})
        manager._activate(board, event)
        self.assertEqual(board.at((3, 3)).kind, "K")
        self.assertIsNone(board.at((3, 4)))
        self.assertIsNone(board.at((4, 3)))

    def test_meteor_can_expose_check(self):
        board, manager = Board(False), EventManager()
        board.add((7, 4), WHITE, "K")
        board.add((0, 0), BLACK, "K")
        board.add((0, 4), BLACK, "R")
        board.add((4, 4), WHITE, "B")
        self.assertFalse(in_check(board, WHITE))
        manager._activate(board, ChaosEvent("meteor", squares={(4, 4)}))
        self.assertTrue(in_check(board, WHITE))

    def test_promotion_expires_without_moving(self):
        board, manager = Board(), EventManager()
        pawn = board.at((6, 0))
        manager.active = ChaosEvent("promotion", targets=[pawn.uid])
        manager._activate(board, manager.active)
        self.assertEqual(pawn.movement_kind(), "Q")
        manager.tick(board)
        manager.tick(board)
        self.assertEqual(pawn.movement_kind(), "P")

    def test_real_promotion_survives_expiry(self):
        board, manager = Board(False), EventManager()
        pawn = board.add((1, 0), WHITE, "P")
        manager.active = ChaosEvent("promotion", targets=[pawn.uid])
        manager._activate(board, manager.active)
        board.apply(Move((1, 0), (0, 0), promotion="N"))
        manager.tick(board)
        manager.tick(board)
        self.assertEqual(pawn.kind, "N")
        self.assertEqual(pawn.movement_kind(), "N")

    def test_peace_is_fixed_ranks_four_five(self):
        board, manager = Board(), EventManager()
        manager.active = manager.make_event(board, "peace")
        manager._activate(board, manager.active)
        self.assertEqual(board.peace_rows, {3, 4})
        manager.tick(board)
        manager.tick(board)
        self.assertFalse(board.peace_rows)

    def test_invalid_event_raises_value_error(self):
        with self.assertRaises(ValueError):
            EventManager().make_event(Board(), "not-an-event")


if __name__ == "__main__":
    unittest.main()

