"""Mouse-to-board interaction tests, using Pygame's off-screen driver."""

import os
import unittest
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
try:
    import pygame
except ImportError:
    pygame = None


class UITests(unittest.TestCase):
    def setUp(self):
        if pygame is None:
            self.skipTest("Install Pygame to run UI interaction tests")
        pygame.display.init()
        pygame.font.init()
        from game import Game
        from ui import UI
        self.game = Game(seed=5)
        self.ui = UI(pygame.display.set_mode((1040, 760)), self.game)

    def tearDown(self):
        pygame.quit()

    def click(self, pos):
        return self.ui.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))

    def test_mouse_move_e2_to_e4(self):
        self.click(self.ui.square_rect((6, 4)).center)
        self.assertEqual(self.game.selected, (6, 4))
        self.click(self.ui.square_rect((4, 4)).center)
        self.assertEqual(self.game.ply, 1)
        self.assertEqual(self.game.turn, "black")

    def test_click_outside_board_is_ignored(self):
        self.click((20, 20))
        self.assertIsNone(self.game.selected)
        self.assertEqual(self.game.ply, 0)

    def test_rules_modal_blocks_board_input(self):
        self.click(self.ui.buttons["help"].center)
        self.assertEqual(self.ui.modal, "help")
        self.click(self.ui.square_rect((6, 4)).center)
        self.assertIsNone(self.game.selected)
        self.assertIsNone(self.ui.modal)

    def test_restart_requires_confirmation(self):
        self.assertIsNone(self.click(self.ui.buttons["new"].center))
        self.assertEqual(self.ui.modal, "new")
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        self.assertEqual(self.ui.handle(event), "restart")

    def test_escape_cancels_selection(self):
        self.click(self.ui.square_rect((6, 4)).center)
        self.ui.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertIsNone(self.game.selected)

    def test_scaled_display_maps_board_and_buttons(self):
        from ui import UI
        for size in ((1920, 1080), (1280, 1024), (800, 600)):
            with self.subTest(size=size):
                from game import Game
                self.game = Game(seed=5)
                self.ui = UI(pygame.display.set_mode(size), self.game)
                self.assertEqual(self.ui.screen.get_size(), self.ui.viewport.size)
                self.assertEqual(self.ui.event_cards["meteor"].get_size(),
                                 self.ui.pixel_point((220, 330)))
                for square in ((6, 4), (4, 4)):
                    x, y = self.ui.square_rect(square).center
                    viewport = self.ui.viewport
                    point = (round(viewport.x + x * viewport.width / 1040),
                             round(viewport.y + y * viewport.height / 760))
                    self.click(point)
                self.assertEqual(self.game.ply, 1)
                x, y = self.ui.buttons["help"].center
                self.click((round(viewport.x + x * viewport.width / 1040),
                            round(viewport.y + y * viewport.height / 760)))
                self.assertEqual(self.ui.modal, "help")
                self.ui.draw()

    def test_exit_button_returns_quit(self):
        self.assertEqual(self.click(self.ui.exit_button.center), "quit")

    def test_all_events_render(self):
        for kind in ("freeze", "promotion", "block", "meteor", "peace"):
            with self.subTest(kind=kind):
                self.game.events.upcoming = self.game.events.make_event(self.game.board, kind)
                self.game.events.cooldown = 2
                self.ui.draw()


if __name__ == "__main__":
    unittest.main()
