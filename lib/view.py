"""This is the view for the game.

There's an image of what I want the board to look like,
"../data/board_snapshot.png".  I'm using that image to figure out the
positions of everything on the board.

"""

import pygame
from pygame.locals import *

from pydispatch import dispatcher

from data import load_image
from model import invert, RED, BLUE, BLANK, SIZE, STATUS_WINNER
from scheduler import scheduler

__docformat__ = 'restructuredtext'

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
BOARD_WIDTH = 402
BOARD_HEIGHT = 700
SQUARE_WIDTH = 101
SQUARE_HEIGHT = 42
BALL_WIDTH = 57
BALL_HEIGHT = 57
BOARD_OFFSET_BOTTOM = 37
BOARD_OFFSET_LEFT = 46
Z_OFFSET_BOTTOM = 243
Y_OFFSET_BOTTOM = 69
Y_OFFSET_LEFT = 46
X_OFFSET_LEFT = 106
BALL_OFFSET_BOTTOM = 20
BALL_OFFSET_LEFT = 22
ANTIALIASED = True
DEFAULT_FONT_SIZE = 48
WHITE = (255, 255, 255)
DEFAULT_FONT_COLOR = WHITE
TEXT_LEFT = 598
LEVEL_TOP = 62
MENU_TOP = 697
LEFT = 0
TOP = 1
MAX_SHOWABLE_STATUS_LINES = 3
ANIMATED_PAUSE = 400


class Board(pygame.sprite.OrderedUpdates):

    """This is a rendering group for all the pieces of the board.

    This is a subclass of pygame.sprite.OrderedUpdates.  Hence, the key
    line is ``pygame.display.update(board.draw(screen))``.

    The following attributes are used:

    balls
      This is a dict mapping tuples of the form ``(x, y, z)`` to
      sprites.  There is one ball for every square, and they're created
      ahead of time.

    """

    def __init__(self, game_model, *args, **kargs):
        """Create all the Squares and Balls."""
        pygame.sprite.OrderedUpdates.__init__(self, *args, **kargs)
        self.balls = {}
        for xyz in game_model.iter_xyz():
            square_model = game_model.board[xyz]
            square_view = Square(square_model)
            self.add(square_view)
            self.balls[xyz] = Ball(self, square_model, square_view)


class Square(pygame.sprite.Sprite):

    """This represents one square on the board.

    The following attributes are used:

    square_model
      This is the associated instance of model.Square.

    """

    def __init__(self, square_model):
        """Setup the square, including position."""
        pygame.sprite.Sprite.__init__(self)
        self.square_model = square_model
        self.image = load_image('normal_square.png')
        self.rect = self.image.get_rect()
        (x, y, z) = square_model.xyz
        # I'm inverting the y to match model.Game.__repr__.
        self.rect.bottom = (SCREEN_HEIGHT - (BOARD_OFFSET_BOTTOM +
                                             z * Z_OFFSET_BOTTOM +
                                             invert(y) * Y_OFFSET_BOTTOM))
        self.rect.left = (BOARD_OFFSET_LEFT + invert(y) * Y_OFFSET_LEFT +
                          x * X_OFFSET_LEFT)
        dispatcher.connect(self.handle_board_changed, 'BOARD CHANGED')

    def handle_board_changed(self):
        """Am I special or not?"""
        name = self.square_model.special and 'special' or 'normal'
        # This is pretty much a NULL operation unless name has changed.
        self.image = load_image('%s_square.png' % name)


class Ball(pygame.sprite.Sprite):

    """This represense a ball on a square.

    The following attributes are used:

    board
      This is the rendering group.  This ball adds itself to the board
      in order to be rendered on an as needed basis.

    square_model
      This is the associated instance of model.Square.

    """

    def __init__(self, board, square_model, square_view):
        """Setup the ball, including position."""
        pygame.sprite.Sprite.__init__(self)
        self.board = board
        self.square_model = square_model
        self.image = load_image('red_ball.png')  # Irrelevent which one.
        self.rect = self.image.get_rect()
        self.rect.bottom = square_view.rect.bottom - BALL_OFFSET_BOTTOM
        self.rect.left = square_view.rect.left + BALL_OFFSET_LEFT
        dispatcher.connect(self.handle_board_changed, signal='BOARD CHANGED')
        dispatcher.connect(self.handle_score_changed, signal='SCORE CHANGED')

    def handle_board_changed(self):
        """Update based on changes to the board."""
        if self.square_model.value == BLANK and self.alive():
            self.remove(self.board)
        elif self.square_model.value != BLANK and not self.alive():
            self.add(self.board)
            self.fix_color()

    def handle_score_changed(self, xyzs_included=[]):
        """Highlight the balls involved.

        We can assume they're already setup.

        """
        if self.square_model.xyz in xyzs_included:
            self.image = load_image('green_ball.png')
            scheduler.set_timer(ANIMATED_PAUSE, self.fix_color)

    def fix_color(self):
        """Set the color to whatever it's supposed to be."""
        for color in ('RED', 'BLUE'):
            if self.square_model.value == globals()[color]:
                # This is pretty much a NULL operation unless it's changed.
                self.image = load_image('%s_ball.png' % color.lower())


class ScoreBoard(pygame.sprite.RenderUpdates):

    """This is a rendering group for all the supplemental text.

    The following attributes are used:

    game_model
      Some of the sprites need this.

    cursor
      This is the topleft of where to insert the next sprite.

    """

    def __init__(self, game_model, *args, **kargs):
        """Create all the sprites."""
        pygame.sprite.RenderUpdates.__init__(self, *args, **kargs)
        self.game_model = game_model
        self.cursor = [TEXT_LEFT, LEVEL_TOP]
        for constructor in (LevelLabel, ScoreLabel, TurnLabel, SpecialLabel):
            self.print_sprite(constructor(game_model))
        for i in range(2):
            self.print_sprite("")
        for i in range(MAX_SHOWABLE_STATUS_LINES):
            self.print_sprite(StatusLabel(game_model, i))
        self.cursor[TOP] = MENU_TOP
        for text in ("(H)elp  ", "(R)eset  ", "(Q)uit  "):
            self.print_sprite(text, newline=False)

    def print_sprite(self, sprite, newline=True):
        """Output the sprite at the cursor and update the cursor.

        sprite
          This is the sprite to print.  If you just give me a string,
          I'll wrap it for you in a sprite.

        newline
          Should we wrap?

        Also, self.add it.

        """
        if isinstance(sprite, basestring):
            sprite = SmartLabel(default_text=sprite)
        sprite.rect.topleft = self.cursor
        self.add(sprite)
        if newline:
            self.cursor[TOP] += sprite.rect.height
        else:
            self.cursor[LEFT] += sprite.rect.width


class SmartLabel(pygame.sprite.Sprite):

    """This is a label that is smart enough to respond to model changes.

    The following attributes are used:

    game_model
      Just in case you need to get values out of it.  This base class
      doesn't use it.

    font
      I'll setup a default font.

    signals_to_listen_for
      By default, this is ().

    default_text
      You can pass this to the constructor.

    """

    signals_to_listen_for = ()

    def __init__(self, game_model=None, default_text=""):
        """Grab the args, setup the signals, etc."""
        pygame.sprite.Sprite.__init__(self)
        self.game_model = game_model
        self.font = pygame.font.Font(None, DEFAULT_FONT_SIZE)
        for signal in self.signals_to_listen_for:
            dispatcher.connect(self.handle_signal, signal=signal)
        self.default_text = default_text
        self.draw_text(self.calc_text())

    def handle_signal(self, signal):
        """Respond to the signal.

        Feel free to override this and actually make use of the signal,
        etc.

        """
        self.draw_text(self.calc_text())

    def calc_text(self):
        """What text should we write?"""
        return self.default_text

    def draw_text(self, text):
        """Draw the text."""
        self.image = self.font.render(text, ANTIALIASED, DEFAULT_FONT_COLOR)
        # Don't lose the topleft, *if* it has one.
        orig_rect = getattr(self, "rect", None)
        self.rect = self.image.get_rect()
        if orig_rect is not None:
            self.rect.topleft = orig_rect.topleft


def square_value_to_string(value):
    """Given RED or BLUE, return 'Red' or 'Blue'."""
    return {RED: "Red", BLUE: "Blue"}[value]


class LevelLabel(SmartLabel):

    """Show the level."""

    signals_to_listen_for = ("LEVEL CHANGED",)

    def calc_text(self):
        # Don't let the level go above SIZE at the end of the game.
        return 'Level: %s' % min(self.game_model.current_level + 1, SIZE)


class ScoreLabel(SmartLabel):

    """Show the score."""

    signals_to_listen_for = ("SCORE CHANGED",)

    def calc_text(self):
        scores = self.game_model.scores
        return "Red: %02d Blue: %02d" % (scores[RED], scores[BLUE])


class TurnLabel(SmartLabel):

    """Show whose turn it is."""

    signals_to_listen_for = ("PLAYER CHANGED",)

    def calc_text(self):
        current_player = self.game_model.current_player
        who = square_value_to_string(current_player)
        return "Current Player: %s" % who


class SpecialLabel(SmartLabel):

    """Tell the user if the next move is special."""

    signals_to_listen_for = ("PLAYER CHANGED",)

    def calc_text(self):
        return ("Next Square: %s" % 
                (self.game_model.current_move_special and "Special!" or
                 "Normal"))


class StatusLabel(SmartLabel):

    """Each of these shows one line of status."""

    signals_to_listen_for = ("STATUS CHANGED",)

    def __init__(self, game_model, line_number):
        self.line_number = line_number  # Must come first.
        SmartLabel.__init__(self, game_model)

    def calc_text(self):
        try:
            (fmt, args) = self.game_model.status[self.line_number]
            if fmt == STATUS_WINNER:
                # "Red" not "X".
                args = (square_value_to_string(args[0]),)
            return fmt % args
        except IndexError:
            return ""
