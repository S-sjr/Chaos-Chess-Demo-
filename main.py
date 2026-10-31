"""
Create the window and run the input and drawing loop.
"""

import argparse
import os


def main():
    args = read_options()
    if os.name == "nt":
        # Prevent Windows display scaling from enlarging the rendered frame.
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    try:
        import pygame
    except ImportError:
        print("Pygame is missing. Run: python -m pip install -r requirements.txt")
        return 1
    import setting as S
    from game import Game
    from ui import UI

    try:
        # Create the window, game state, and interface.
        pygame.display.init()
        pygame.font.init()
        if args.windowed or args.headless:
            screen = pygame.display.set_mode((S.WIDTH, S.HEIGHT))
        else:
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption("Chaos Chess | COMP9001")
        game = Game(seed=args.seed)
        ui = UI(screen, game)
        clock = pygame.time.Clock()
        running = True
        frames = 0
        while running:
            # Handle player input and restart requests.
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    action = ui.handle(event)
                    if action == "restart":
                        game = Game(seed=args.seed)
                        ui.game = game
                    elif action == "quit":
                        running = False

            # Refresh the display at the target frame rate.
            ui.draw()
            pygame.display.flip()
            clock.tick(S.FPS)
            frames += 1
            if args.frames and frames >= args.frames:
                running = False
        if args.screenshot:
            pygame.image.save(screen, args.screenshot)
    except (pygame.error, OSError) as error:
        print("Could not run Chaos Chess:", error)
        return 1
    finally:
        # Release Pygame resources on exit.
        pygame.quit()
    return 0


def read_options():
    """Read optional launch and rendering arguments."""
    parser = argparse.ArgumentParser(description="Chaos Chess - local two-player chess")
    parser.add_argument("--windowed", action="store_true", help="Open in a window instead of fullscreen")
    parser.add_argument("--seed", type=int, help="Reproduce an event sequence during testing")
    parser.add_argument("--headless", action="store_true", help="Render without opening a window")
    parser.add_argument("--frames", type=int, default=0, help="Exit after N frames (0 = unlimited)")
    parser.add_argument("--screenshot", help="Save the last frame as a PNG before exit")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
