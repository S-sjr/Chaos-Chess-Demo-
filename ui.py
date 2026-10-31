"""
Draw the board and panels and handle player input.
"""

import math
from pathlib import Path
import pygame
import setting as S
from events import EVENT_NAMES, DESCRIPTIONS
from piece import WHITE, BLACK, PROMOTIONS
from rules import in_check


class UI:
    def __init__(self, screen, game):
        self.display = screen
        scale = min(screen.get_width() / S.WIDTH, screen.get_height() / S.HEIGHT)
        size = (round(S.WIDTH * scale), round(S.HEIGHT * scale))
        self.viewport = pygame.Rect((0, 0), size)
        self.viewport.center = screen.get_rect().center
        self.scale = scale
        self.screen = pygame.Surface(size).convert()
        self.game = game
        # Render the bundled font directly at the display resolution.
        font_path = Path(__file__).resolve().parent / "assets" / "fonts" / "LilitaOne-Regular.ttf"
        self.font = pygame.font.Font(str(font_path), round(18 * scale))
        self.small = pygame.font.Font(str(font_path), round(15 * scale))
        self.bold = pygame.font.Font(str(font_path), round(20 * scale))
        self.title = pygame.font.Font(str(font_path), round(30 * scale))
        self.modal = None
        self.buttons = {
            "new": pygame.Rect(S.PANEL_X, 686, 100, 38),
            "help": pygame.Rect(S.PANEL_X + 112, 686, 100, 38),
            "draw": pygame.Rect(S.PANEL_X + 224, 686, 104, 38),
        }
        self.exit_button = pygame.Rect(944, 20, 64, 32)
        self.promotion_buttons = []
        for index in range(4):
            self.promotion_buttons.append(pygame.Rect(335 + index * 92, 364, 78, 80))

        # Load and cache each piece image once.
        self.icons = {}
        for color in (WHITE, BLACK):
            for kind in "KQRBNP":
                self.icons[(color, kind)] = self._piece_icon(color, kind)

        self.event_cards = self._load_event_cards()
        self.board_image = self._load_board_image()

    def pixel_point(self, point):
        """Convert layout coordinates to native pixels."""
        return (round(point[0] * self.viewport.width / S.WIDTH),
                round(point[1] * self.viewport.height / S.HEIGHT))

    def pixel_rect(self, rect):
        rect = pygame.Rect(rect)
        left, top = self.pixel_point(rect.topleft)
        right, bottom = self.pixel_point(rect.bottomright)
        return pygame.Rect(left, top, right - left, bottom - top)

    def draw_rect(self, color, rect, width=0, border_radius=0):
        pygame.draw.rect(self.screen, color, self.pixel_rect(rect),
                         round(width * self.scale),
                         border_radius=round(border_radius * self.scale))

    def draw_circle(self, color, center, radius, width=0):
        pygame.draw.circle(self.screen, color, self.pixel_point(center),
                           round(radius * self.scale), round(width * self.scale))

    def draw_line(self, color, start, end, width=1):
        pygame.draw.line(self.screen, color, self.pixel_point(start),
                         self.pixel_point(end), max(1, round(width * self.scale)))

    def render_text(self, value, color, font):
        """Render crisp text with a thin outline on headings."""
        face = font.render(value, True, color)
        if font not in (self.bold, self.title):
            return face
        edge = max(1, round(self.scale))
        image = pygame.Surface((face.get_width() + edge * 2,
                                face.get_height() + edge * 2), pygame.SRCALPHA)
        outline = font.render(value, True, (8, 12, 16))
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            image.blit(outline, (edge + dx * edge, edge + dy * edge))
        image.blit(face, (edge, edge))
        return image

    def text(self, value, position, color=S.TEXT, font=None):
        if font is None:
            font = self.font
        text_image = self.render_text(value, color, font)
        self.screen.blit(text_image, self.pixel_point(position))

    def wrapped(self, value, x, y, width, color=S.MUTED, font=None, line_height=23):
        """Wrap text to the given width and return the next line position."""
        if font is None:
            font = self.font
        line = ""
        for word in value.split():
            candidate = (line + " " + word).strip()
            if line and font.size(candidate)[0] > round(width * self.scale):
                self.text(line, (x, y), color, font)
                y += line_height
                line = word
            else:
                line = candidate
        if line:
            self.text(line, (x, y), color, font)
            y += line_height
        return y

    def square_rect(self, square):
        """Convert board coordinates to a screen rectangle."""
        row, column = square
        x = S.BOARD_X + column * S.SQUARE
        y = S.BOARD_Y + row * S.SQUARE
        return pygame.Rect(x, y, S.SQUARE, S.SQUARE)

    def _piece_icon(self, color, kind):
        """Load a transparent piece image and fit it at native display resolution."""
        names = {"K": "king", "Q": "queen", "R": "rook",
                 "B": "bishop", "N": "knight", "P": "pawn"}
        heights = {"K": 58, "Q": 57, "B": 54, "N": 52, "R": 48, "P": 42}
        # Resolve assets relative to this file.
        folder = Path(__file__).resolve().parent / "assets" / "pieces"
        filename = color + "_" + names[kind] + ".png"
        path = folder / filename
        try:
            source = pygame.image.load(str(path)).convert_alpha()
        except (pygame.error, OSError) as error:
            raise pygame.error("Could not load chess piece: " + str(path)) from error
        bounds = source.get_bounding_rect(min_alpha=32)
        if bounds.width == 0 or bounds.height == 0:
            raise pygame.error("Chess piece image is empty: " + str(path))
        artwork = source.subsurface(bounds)
        # Fit the artwork without stretching it.
        scale = min(52 / bounds.width, heights[kind] / bounds.height) * self.scale
        width = max(1, round(bounds.width * scale))
        height = max(1, round(bounds.height * scale))
        size = (width, height)
        sprite = pygame.transform.smoothscale(artwork, size)
        image = pygame.Surface(self.pixel_point((64, 64)), pygame.SRCALPHA)
        image.blit(sprite, ((image.get_width() - size[0]) // 2, round(60 * self.scale) - size[1]))
        return image

    def _overlay(self, rect, color, alpha):
        """Draw a translucent color over a rectangle."""
        rect = self.pixel_rect(rect)
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        red, green, blue = color
        surface.fill((red, green, blue, alpha))
        self.screen.blit(surface, rect)

    def draw(self):
        self.screen.fill(S.BACKGROUND)
        self.text("CHAOS / CHESS", (40, 20), S.TEXT, self.title)
        self._draw_board()
        self._draw_panel()
        if self.game.pending_promotion:
            self._draw_promotion()
        elif self.modal:
            self._draw_modal()
        # Present the native-resolution canvas without resampling.
        self.display.fill(S.BACKGROUND)
        self.display.blit(self.screen, self.viewport)

    def _load_board_image(self):
        """Fit the board artwork to the native-pixel playing area."""
        path = Path(__file__).resolve().parent / "assets" / "board" / "board.png"
        try:
            source = pygame.image.load(str(path)).convert()
        except (pygame.error, OSError) as error:
            raise pygame.error("Could not load board image: " + str(path)) from error
        rect = self.pixel_rect(pygame.Rect(S.BOARD_X, S.BOARD_Y,
                                          S.BOARD_SIZE, S.BOARD_SIZE))
        return pygame.transform.smoothscale(source, rect.size)

    def _draw_board(self):
        board = self.game.board
        area = pygame.Rect(S.BOARD_X, S.BOARD_Y, S.BOARD_SIZE, S.BOARD_SIZE)
        self.draw_rect((27, 47, 64), area.inflate(16, 16), border_radius=5)
        self.draw_rect((78, 113, 139), area.inflate(12, 12), 2, border_radius=4)
        self.screen.blit(self.board_image, self.pixel_point(area.topleft))

        # Collect legal destinations and checked kings before drawing.
        targets = set()
        if self.game.selected is not None:
            for move in self.game.selected_moves():
                targets.add(move.end)

        checked = []
        for color in (WHITE, BLACK):
            if in_check(board, color):
                checked.append(board.king(color))

        forecast_targets = []
        if self.game.events.upcoming is not None:
            forecast_targets = self.game.events.upcoming.targets

        for row in range(8):
            for column in range(8):
                square = (row, column)
                rect = self.square_rect(square)
                self._draw_square_background(square, rect)

                if square in checked:
                    self.draw_rect(S.METEOR, rect.inflate(-4, -4), 4)

                piece = board.at(square)
                if piece is not None:
                    self._draw_piece(piece, rect, forecast_targets)

                if square in targets:
                    if piece is not None:
                        self.draw_circle((216, 163, 66), rect.center, 33, 4)
                    else:
                        self.draw_circle(S.ACCENT, rect.center, 8)
                if square == self.game.selected:
                    self.draw_rect(S.ACCENT, rect.inflate(-3, -3), 4)

        # Label ranks and files along the board edges.
        letters = "abcdefgh"
        for index in range(8):
            rank_position = (19, S.BOARD_Y + index * S.SQUARE + 27)
            file_position = (S.BOARD_X + index * S.SQUARE + 33, 693)
            self.text(str(8 - index), rank_position, S.MUTED, self.small)
            self.text(letters[index], file_position, S.MUTED, self.small)

    def _draw_square_background(self, square, rect):
        board = self.game.board
        row, column = square

        if row in board.peace_rows:
            self._overlay(rect, S.PEACE, 92)
        if board.last_move is not None:
            if square in (board.last_move.start, board.last_move.end):
                self._overlay(rect, S.ACCENT, 70)

        preview = self.game.events.upcoming
        if preview is not None and square in preview.squares:
            if preview.kind == "meteor":
                # Animate the warning without advancing the turn countdown.
                time_value = pygame.time.get_ticks() / 240
                brightness = (1 + math.sin(time_value)) / 2
                alpha = int(80 + 55 * brightness)
                self._overlay(rect, S.METEOR, alpha)
                self.draw_rect(S.METEOR, rect.inflate(-6, -6), 2)
            else:
                color = S.ACCENT
                if preview.kind == "peace":
                    color = S.PEACE
                self.draw_rect(color, rect.inflate(-6, -6), 2)

        if square in board.blocked:
            self._draw_block(rect)

    def _draw_block(self, rect):
        self._overlay(rect, (29, 40, 49), 190)
        for offset in (16, 32, 48):
            start = (rect.x + 10, rect.y + offset)
            end = (rect.x + offset, rect.y + 10)
            self.draw_line(S.MUTED, start, end, 2)
        self.draw_line(S.ACCENT,
                         (rect.x + 15, rect.y + 15), (rect.right - 15, rect.bottom - 15), 3)
        self.draw_line(S.ACCENT,
                         (rect.right - 15, rect.y + 15), (rect.x + 15, rect.bottom - 15), 3)

    def _draw_piece(self, piece, rect, forecast_targets):
        image = self.icons[(piece.color, piece.movement_kind())]
        self.screen.blit(image, self.pixel_point((rect.x + 6, rect.y + 5)))

        if piece.uid in forecast_targets:
            self.draw_rect(S.ACCENT, rect.inflate(-9, -9), 2, border_radius=8)
            self.text("!", (rect.right - 16, rect.y + 3), (60, 45, 20), self.bold)
        if piece.frozen:
            self._overlay(rect.inflate(-5, -5), S.ICE, 85)
            self.draw_rect(S.ICE, rect.inflate(-6, -6), 3, border_radius=7)
            self.text("ICE", (rect.x + 6, rect.y + 3), (20, 65, 100), self.small)
        if piece.temporary_queen:
            self.text("P > Q", (rect.x + 5, rect.y + 2), (78, 47, 10), self.small)


    def _card(self, rect, label):
        self.draw_rect(S.PANEL, rect, border_radius=12)
        self.text(label, (rect.x+16, rect.y+12), S.MUTED, self.small)

    def _load_event_cards(self):
        """Load each event card once at its display size."""
        folder = Path(__file__).resolve().parent / "assets" / "events"
        cards = {}
        for kind in list(EVENT_NAMES) + ["back"]:
            path = folder / (kind + ".png")
            try:
                source = pygame.image.load(str(path)).convert_alpha()
            except (pygame.error, OSError) as error:
                raise pygame.error("Could not load event card: " + str(path)) from error
            cards[kind] = pygame.transform.smoothscale(source, self.pixel_point((220, 330)))
        return cards

    def canvas_position(self, position):
        """Convert display coordinates to the fixed game canvas."""
        x, y = position
        return ((x - self.viewport.x) * S.WIDTH / self.viewport.width,
                (y - self.viewport.y) * S.HEIGHT / self.viewport.height)

    def _draw_card_back(self, rect):
        """Draw the shared blue back at native resolution."""
        self.screen.blit(self.event_cards["back"], self.pixel_point(rect.topleft))

    def _draw_event_stack(self):
        """Show the active event or announced forecast above hidden card backs."""
        manager = self.game.events
        event = manager.active
        label = "CURRENT EVENT"
        timing = ""
        if event is not None:
            timing = "Ends in " + str(event.remaining) + " turn(s)"
        elif manager.upcoming is not None:
            event = manager.upcoming
            label = "UP NEXT / FORECAST"
            timing = "Starts in " + str(manager.cooldown) + " turn(s)"
            if event.kind == "meteor":
                timing = "Impact in " + str(manager.cooldown) + " turn(s)"
        else:
            label = "EVENT DECK"

        x = S.PANEL_X
        self.text(label, (x + 16, 192), S.ACCENT, self.small)
        # Hidden backs do not reveal unannounced events.
        for layer in range(5, 0, -1):
            back = pygame.Rect(x + 24 + layer * 14, 242 - layer * 6, 220, 330)
            self._draw_card_back(back)
        front = pygame.Rect(x + 24, 242, 220, 330)
        if event is not None:
            self.screen.blit(self.event_cards[event.kind], self.pixel_point(front.topleft))
        else:
            self._draw_card_back(front)
            turns = max(0, manager.cooldown - S.WARNING_TURNS)
            timing = "Forecast in " + str(turns) + " turn(s)"

        self.text(timing, (x + 16, 590), S.ACCENT, self.bold)
        description = "No active event. The next event will be revealed before it begins."
        if event is not None:
            description = event.description
        self.wrapped(description, x + 16, 622, S.PANEL_WIDTH - 32,
                     S.MUTED, self.small, 19)

    def _draw_panel(self):
        game = self.game
        x = S.PANEL_X
        rect = pygame.Rect(x, 80, S.PANEL_WIDTH, 100)
        self._card(rect, "TURN " + str(game.ply+1))
        status = game.turn.title() + " to move"
        if game.result is not None:
            status = game.result
        if not game.result and in_check(game.board, game.turn):
            status += "  /  CHECK"
        if game.result is None and game.message.startswith("No draw claim"):
            status = game.message
        self.wrapped(status, x+16, 116, S.PANEL_WIDTH-32, S.TEXT, self.bold, 20)
        self._draw_event_stack()
        mouse = self.canvas_position(pygame.mouse.get_pos())
        self.draw_rect(S.PANEL, self.exit_button, border_radius=7)
        self.text("Exit", (self.exit_button.x + 18, self.exit_button.y + 8),
                  S.TEXT, self.small)
        for name, label in (("new", "New game"), ("help", "Rules"), ("draw", "Claim draw")):
            rect = self.buttons[name]
            color = S.PANEL
            if rect.collidepoint(mouse):
                color = (62, 77, 88)
            self.draw_rect(color, rect, border_radius=7)
            text = self.small.render(label, True, S.TEXT)
            self.screen.blit(text, text.get_rect(center=self.pixel_point(rect.center)))

    def _veil(self):
        self._overlay(pygame.Rect(0, 0, S.WIDTH, S.HEIGHT), (0, 0, 0), 175)

    def _draw_promotion(self):
        self._veil()
        self.draw_rect(S.PANEL, (293, 272, 454, 210), border_radius=16)
        self.text("Choose your promotion", (322, 292), S.TEXT, self.title)
        self.text("Permanent promotion overrides temporary effects.", (322, 337), S.MUTED, self.small)
        for index in range(len(PROMOTIONS)):
            kind = PROMOTIONS[index]
            rect = self.promotion_buttons[index]
            self.draw_rect((66, 83, 87), rect, border_radius=8)
            self.screen.blit(self.icons[(self.game.turn, kind)], self.pixel_point((rect.x+7, rect.y+2)))
            self.text(kind, (rect.centerx-5, rect.bottom-20), S.TEXT, self.small)

    def _draw_modal(self):
        self._veil()
        if self.modal == "new":
            self.draw_rect(S.PANEL, (290, 280, 460, 180), border_radius=16)
            self.text("Start a new game?", (320, 304), S.TEXT, self.title)
            self.text("This will clear the current match.", (320, 353))
            self.text("ENTER / click here to restart.  ESC to cancel.", (320, 404), S.ACCENT, self.small)
            return
        self.draw_rect(S.PANEL, (160, 44, 720, 672), border_radius=16)
        self.text("HOW TO PLAY", (190, 65), S.TEXT, self.title)
        y = self.wrapped("Click your piece, then a highlighted square. White starts. Invalid clicks use no turns. Escape cancels selection; promotion offers Q / R / B / N.", 190, 112, 660)
        y = self.wrapped("One turn = one completed move. Events last 2 turns, then 4 clear turns follow. The last 2 clear turns show the next forecast. Meteor is instantaneous.", 190, y+9, 660)
        for kind, title in EVENT_NAMES.items():
            self.text(title, (190, y+8), S.ACCENT, self.bold)
            y = self.wrapped(DESCRIPTIONS[kind], 190, y+36, 660, font=self.small, line_height=20)
        self.wrapped("Kings ignore direct event effects, but indirect checks and checkmates count. A checked king must be rescued on its owner's next turn. Announced targets may escape or be captured; occupied block targets are skipped.", 190, y+12, 660, font=self.small, line_height=20)
        self.text("Click anywhere to close", (190, 681), S.TEXT, self.small)

    def handle(self, event):
        """Handle input and return restart when a new game is confirmed."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.modal:
                    self.modal = None
                else:
                    self.game.cancel_selection()
            elif event.key == pygame.K_RETURN and self.modal == "new":
                self.modal = None
                return "restart"
            return None
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        position = self.canvas_position(event.pos)
        if self.exit_button.collidepoint(position):
            return "quit"
        if self.game.pending_promotion:
            for index in range(len(PROMOTIONS)):
                kind = PROMOTIONS[index]
                rect = self.promotion_buttons[index]
                if rect.collidepoint(position):
                    self.game.choose_promotion(kind)
            return None
        if self.modal:
            if self.modal == "new":
                if pygame.Rect(290, 390, 460, 70).collidepoint(position):
                    self.modal = None
                    return "restart"
                return None
            self.modal = None
            return None
        for name, rect in self.buttons.items():
            if rect.collidepoint(position):
                if name == "draw":
                    self.game.claim_draw()
                else:
                    self.modal = name
                return None
        board_rect = pygame.Rect(S.BOARD_X, S.BOARD_Y, S.BOARD_SIZE, S.BOARD_SIZE)
        if board_rect.collidepoint(position):
            # Convert the mouse position to board coordinates.
            mouse_x, mouse_y = position
            row = (mouse_y - S.BOARD_Y) // S.SQUARE
            column = (mouse_x - S.BOARD_X) // S.SQUARE
            self.game.click_square((int(row), int(column)))
        return None


