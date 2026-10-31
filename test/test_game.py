"""Test complete turns, promotion input, and game termination."""

import unittest
from board import Board
from events import ChaosEvent
from game import Game
from piece import WHITE, BLACK, Move


def move(game, start, end, promotion=None):
    """Find and play a legal move with the given coordinates."""
    for candidate in game.moves:
        if candidate.start == start and candidate.end == end:
            if candidate.promotion == promotion:
                game.play(candidate)
                return
    raise AssertionError("The expected move is not legal.")


class GameTests(unittest.TestCase):
    def test_invalid_click_does_not_consume_turn(self):
        game = Game()
        game.click_square((6, 4))
        game.click_square((3, 4))
        self.assertEqual(game.ply, 0)
        self.assertEqual(game.events.cooldown, 4)
        self.assertEqual(game.turn, WHITE)

    def test_click_move_switches_player(self):
        game = Game()
        game.click_square((6, 4))
        game.click_square((4, 4))
        self.assertEqual(game.ply, 1)
        self.assertEqual(game.turn, BLACK)
        self.assertEqual(game.board.at((4, 4)).kind, "P")

    def test_fools_mate(self):
        game = Game(chaos=False)
        move(game, (6, 5), (5, 5))
        move(game, (1, 4), (3, 4))
        move(game, (6, 6), (4, 6))
        move(game, (0, 3), (4, 7))
        self.assertEqual(game.result, "Black wins by checkmate.")

    def test_promotion_waits_for_choice(self):
        game = Game(chaos=False)
        game.board = Board(False)
        game.board.add((7, 4), WHITE, "K")
        game.board.add((0, 4), BLACK, "K")
        game.board.add((1, 0), WHITE, "P")
        game.refresh_moves()
        game.click_square((1, 0))
        game.click_square((0, 0))
        self.assertEqual(len(game.pending_promotion), 4)
        self.assertEqual(game.ply, 0)
        game.choose_promotion("R")
        self.assertEqual(game.ply, 1)
        self.assertEqual(game.board.at((0, 0)).kind, "R")

    def test_cancel_promotion_preserves_board(self):
        game = Game(chaos=False)
        game.board = Board(False)
        game.board.add((7, 4), WHITE, "K")
        game.board.add((0, 4), BLACK, "K")
        game.board.add((1, 0), WHITE, "P")
        game.refresh_moves()
        game.click_square((1, 0))
        game.click_square((0, 0))
        game.cancel_selection()
        self.assertEqual(game.ply, 0)
        self.assertEqual(game.board.at((1, 0)).kind, "P")

    def test_threefold_draw_claim(self):
        game = Game(chaos=False)
        for _ in range(2):
            move(game, (7, 6), (5, 5))
            move(game, (0, 6), (2, 5))
            move(game, (5, 5), (7, 6))
            move(game, (2, 5), (0, 6))
        game.claim_draw()
        self.assertEqual(game.result, "Draw claimed: threefold repetition.")

    def test_unavailable_draw_claim_preserves_game(self):
        game = Game()
        game.claim_draw()
        self.assertIsNone(game.result)
        self.assertEqual(game.ply, 0)

    def test_invalid_move_raises_without_mutation(self):
        game = Game()
        with self.assertRaises(ValueError):
            game.play(Move((6, 4), (2, 4)))
        self.assertEqual(game.ply, 0)
        self.assertIsNotNone(game.board.at((6, 4)))

    def test_event_meteor_causes_checkmate(self):
        game = Game()
        game.board = Board(False)
        game.board.add((0, 0), BLACK, "K")
        game.board.add((2, 1), WHITE, "K")
        game.board.add((7, 0), WHITE, "R")
        game.board.add((2, 3), WHITE, "B")
        game.board.add((3, 0), BLACK, "N")
        game.board.add((3, 1), BLACK, "P")
        game.board.add((6, 7), WHITE, "P")
        game.events.cooldown = 1
        game.events.upcoming = ChaosEvent("meteor", squares={(2, 0), (2, 1), (3, 0), (3, 1)})
        game.refresh_moves()
        move(game, (6, 7), (5, 7))
        self.assertEqual(game.result, "White wins by checkmate.")
        self.assertIsNotNone(game.board.at((2, 1)))

    def test_stalemate(self):
        game = Game(chaos=False)
        game.board = Board(False)
        game.board.add((0, 0), BLACK, "K")
        game.board.add((2, 2), WHITE, "K")
        game.board.add((3, 1), WHITE, "Q")
        game.refresh_moves()
        move(game, (3, 1), (2, 1))
        self.assertEqual(game.result, "Draw: stalemate.")


if __name__ == "__main__":
    unittest.main()

