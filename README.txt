CHAOS CHESS
===========

A familiar board. A different decision every game.

Chaos Chess is a local two-player chess game built with Python and Pygame.
It adds announced random events to the chessboard: pieces freeze, paths close,
pawns borrow a queen's power, and meteors threaten the centre of the board.

The idea is to make familiar positions less predictable and encourage players
to adapt instead of relying only on memorised openings. Every event is
announced before it begins, giving both players time to respond.


FEATURES
--------

- Play against a friend on the same computer using mouse controls.
- Explore five events that change movement, captures and board safety.
- See the active event or upcoming forecast in an illustrated card stack.
- Read event descriptions and turn countdowns beside the board.
- Play fullscreen at your desktop resolution, or use windowed mode.
- Use standard chess moves, including castling, en passant and promotion.

This demo currently supports local two-player matches. Computer opponents,
online multiplayer, clocks and saving/loading are not included.


GETTING STARTED
---------------

Requires Python 3.10 or newer and Pygame 2.6.1.
Run the commands below from the folder containing main.py.
Keep the assets folder alongside the Python files.

This is a desktop GUI game and requires a graphical display. Interactive
gameplay is not supported in the Ed terminal. Download the complete project
and run it locally. Pygame is an external dependency.

Install the dependency and start the game:

    python -m pip install -r requirements.txt
    python main.py

For windowed mode:

    python main.py --windowed

On systems where Python 3 is named python3, use python3 instead of python
in these commands. The headless command in DEVELOPMENT only creates a
preview image; it does not provide interactive gameplay.


HOW TO PLAY
-----------

White moves first. Click one of your pieces to highlight its legal destinations,
then click a destination to move. Click another friendly piece to change your
selection, or click the selected piece again to cancel. Escape also cancels.

When a pawn promotes, choose a queen, rook, bishop or knight in the popup.
Invalid clicks and opening the rules do not use a turn.

Buttons:
- Rules: view the movement and event guide.
- New game: restart after confirmation.
- Claim draw: claim an eligible threefold repetition or 50-move draw.
- Exit: close the game. The current match is not saved.


THE EVENTS
----------

Frozen Front
    Up to two non-king pieces on each side cannot move or attack for two turns.
    They still block their squares and can be captured.

Borrowed Crown
    One pawn per side, where available, gains queen movement for two turns.
    Permanent promotion remains permanent when the effect expires.

Fractured Ground
    Six separated empty squares are chosen for blocking. Non-kings cannot
    land on blocked squares, and sliding pieces cannot pass through them.
    Knights can jump over them. Targets occupied at activation are skipped.

Meteor Strike
    A random 2 x 2 area within ranks 3-6 flashes red during the warning.
    At impact, all non-king pieces in those squares are destroyed.

Sanctuary
    Non-king pieces on ranks 4 and 5 are protected from capture by non-kings.
    Capturing from inside the zone to outside is allowed.

Kings are immune to direct event effects, but events can still create checks
and checkmates. For detailed interactions and draw rules, see docs/game_rules.md.


WHEN EVENTS HAPPEN
------------------

One turn means one player's completed move.

A match starts with four clear turns. The first event is announced after
turn 2 and activates after turn 4. Lasting effects remain for two turns,
followed by four clear turns before the next activation. Each forecast is
shown during the last two clear turns.

Meteor Strike resolves immediately at impact. Events do not overlap.
The front card shows the active event or announced forecast; the cards
behind it remain face down until an event is revealed.


PROJECT LAYOUT
--------------

main.py       Starts the application and runs the game loop.
game.py       Manages turns, player input and match results.
board.py      Stores the board and applies moves.
piece.py      Defines pieces and moves.
rules.py      Checks attacks and legal moves.
events.py     Selects targets and manages event timing.
ui.py         Draws the board, cards, controls and overlays.
setting.py    Contains layout, colour and timing settings.
assets/       Contains chess pieces, cards, board artwork and the UI font.
test/         Contains automated tests.
docs/         Contains detailed rules and development notes.


DEVELOPMENT
-----------

Run the tests using the project environment:

    python -m unittest discover -s test -v

Use a fixed random seed to reproduce an event sequence:

    python main.py --seed 10

Render a short session without opening a window:

    python main.py --headless --frames 2 --screenshot preview.png


CREDITS
-------

Built with Python and Pygame:
    https://www.python.org/
    https://www.pygame.org/

UI font: Lilita One, distributed with its SIL Open Font License.
The font and license are included in assets/fonts/.
    https://github.com/google/fonts/tree/main/ofl/lilitaone

Chess-piece, event-card and board artwork was created or edited with
AI image-generation tools using visual references and iterative adjustments.
Card and board generation notes are included alongside their assets.

