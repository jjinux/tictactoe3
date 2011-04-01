"""This is the model for the game.

See ../data/help.html for the rules.

"""

from cStringIO import StringIO
import random

from pydispatch import dispatcher

__docformat__ = 'restructuredtext'

BLANK = '_'
RED = 'X'
BLUE = 'O'
SPECIAL = '*'

SIZE = 3                        # The width of the board
SQUARES_PER_LEVEL = SIZE ** 2
TOTAL_SQUARES = SIZE ** 3
SPECIAL_SQUARES = (1, 2, 6, 7)  # Remember, 0-based.
RANGE_SIZE = range(SIZE)
RANGE_SIZE_REVERSED = range(SIZE)
RANGE_SIZE_REVERSED.reverse()
TICTACTOE_VALUE = 1
SPECIAL_TICTACTOE_VALUE = 2

STATUS_ONLY_UP = 'The only way is up!'
STATUS_TIE = 'A tie!'
STATUS_WINNER = '%s wins!!!'
STATUS_POINTS_EARNED = '%s point%s!'


class Game:

    """This represents the state of the game.

    Here are some initial properties:

    board
      This is a dict mapping tuples of the form ``(x, y, z)`` to
      instances of Square.  The z represents the level.

    scores
      This is a dict representing the scores, starting with
      ``{RED: 0, BLUE: 0}``.

    move_count
      This starts at 0 and ends at TOTAL_SQUARES.  Keeping a count makes
      it easy to determine whose turn it is (if we know who's first),
      what level we're on, and which moves result in special squares.

    first_player
      Who gets to make the first move?

    status
      This is a list of tuples of the form ``(fmt, args)``
      containing status messages.  It gets reset on every move.  The
      fmts are defined as constants above.

    The following pydispatch signals are sent:

    "LEVEL CHANGED"
      The level has changed.

    "SCORE CHANGED"(xyzs_included)
      The score has changed.  The squares involved are in xyzs_included
      so that you can highlight them.

    "BOARD CHANGED"
      The board has changed.

    "PLAYER CHANGED"
      We just switched players.

    "STATUS CHANGED"
      There are new status messages.

    """

    def __init__(self, first_player=None):
        """Initialize to defaults.
        
        first_player
          If None, I'll pick randomly.

        """
        self.board = {}
        for xyz in self.iter_xyz():
            self.board[xyz] = Square(xyz)
        self.scores = {}
        self.reset(first_player)

    def reset(self, first_player=None):
        """Reset to defaults.
        
        first_player
          If None, I'll pick randomly.

        """
        if first_player is None:
            first_player = random.choice([RED, BLUE])
        self.first_player = first_player
        for square in self.board.values():
            square.reset()
        for i in (RED, BLUE):
            self.scores[i] = 0
        self.move_count = 0
        self.status = []
        for signal in ("LEVEL CHANGED", "SCORE CHANGED", "BOARD CHANGED", 
                       "PLAYER CHANGED", "STATUS CHANGED"):
            dispatcher.send(signal=signal, sender=self)

    def iter_xyz(self):
        """Iterate over every square on the board.

        At each iteration, return ``(x, y, z)``.

        """
        for x in RANGE_SIZE:
            for y in RANGE_SIZE:
                for z in RANGE_SIZE:
                    yield (x, y, z)

    def __repr__(self):
        """Output the game state."""
        buf = StringIO()
        for z in RANGE_SIZE_REVERSED:  # The only way is up!
            buf.write('Level: %s\n' % (z + 1))
            buf.write('--------\n')
            for y in RANGE_SIZE:
                for x in RANGE_SIZE:
                    square = self.board[(x, y, z)]
                    buf.write(repr(square) + ' ')
                buf.write('\n')
            buf.write('\n')
        if not self.done:
            buf.write('[Level: %s] ' % (self.current_level + 1))
            buf.write("[%s's turn] " % self.current_player)
            buf.write("[Special: %s] " %
                      (self.current_move_special and SPECIAL or '_'))
        buf.write('[Score %s:%02d %s:%02d] ' %
                  (RED, self.scores[RED],
                   BLUE, self.scores[BLUE]))
        buf.write('\n')
        return buf.getvalue()

    def done():
        doc = """Is the game done?"""

        def fget(self):
            return self.move_count == TOTAL_SQUARES

        return locals()
    done = property(**done())

    def current_level():
        doc = """What level are we on?"""

        def fget(self):
            return self.move_count // SQUARES_PER_LEVEL

        return locals()
    current_level = property(**current_level())

    def current_player():
        doc = """Whose turn is it?"""

        def fget(self):
            odd = self.move_count % 2
            if odd:
                return self.other_player(self.first_player)
            else:
                return self.first_player

        return locals()
    current_player = property(**current_player())

    def current_move_special():
        doc = """Is the current move special?"""

        def fget(self):
            return self.move_count % SQUARES_PER_LEVEL in SPECIAL_SQUARES

        return locals()
    current_move_special = property(**current_move_special())

    def winner():
        doc = """Get the current winner, or None if tied."""

        def fget(self):
            difference = self.scores[RED] - self.scores[BLUE]
            if difference == 0:
                return None
            elif difference > 0:
                return RED
            else:
                return BLUE

        return locals()
    winner = property(**winner())

    def other_player(self, player):
        """Given a player, return the other player."""
        if player == RED:
            return BLUE
        return RED

    def move(self, (x, y, z)):
        """Let the current player pick a square on the current level.

        Raise a ValueError if:

         * The square is already taken.
         
         * z doesn't match ``self.current_level``.

        """
        if z != self.current_level:
            raise ValueError("Wrong level")
        square = self.board[(x, y, z)]
        if not square.value == BLANK:
            raise ValueError('Square taken')
        self.status = []
        square.value = self.current_player
        square.special = self.current_move_special
        dispatcher.send(signal="BOARD CHANGED", sender=self)
        self._handle_tictactoe((x, y, z))
        self.move_count += 1
        dispatcher.send(signal="PLAYER CHANGED", sender=self)
        new_level = self.move_count % SQUARES_PER_LEVEL == 0
        if new_level:
            dispatcher.send(signal="LEVEL CHANGED", sender=self)
        if 0 < self.move_count and not self.done and new_level:
            self.status.append((STATUS_ONLY_UP, ()))
        if self.done:
            winner = self.winner
            if not winner:
                self.status.append((STATUS_TIE, ()))
            else:
                self.status.append((STATUS_WINNER, (winner,)))
        dispatcher.send(signal="STATUS CHANGED", sender=self)

    def _handle_tictactoe(self, (x, y, z)):
        """Look for and handle instances of tic-tac-toe."""
        if not hasattr(self, '_winning_paths'):
            self._calc_winning_paths()
        points_earned = 0
        xyzs_included = []
        for path in self._winning_paths:
            (x_, y_, z_) = path[0]
            if z < z_:
                # The only way is up!
                continue
            if (x, y, z) not in path:
                # Current point not in path
                continue
            hits = 0
            special_hits = 0
            for xyz in path:
                if self.board[xyz].value == self.current_player:
                    hits += 1
                    if self.board[xyz].special:
                        special_hits += 1
            if hits == SIZE:
                xyzs_included.extend(path)
            if special_hits == SIZE:  # Worth more, so check first.
                points_earned += SPECIAL_TICTACTOE_VALUE
            elif hits == SIZE:
                points_earned += TICTACTOE_VALUE
        if points_earned:
            self.scores[self.current_player] += points_earned
            dispatcher.send(signal="SCORE CHANGED", sender=self,
                            xyzs_included=xyzs_included)
            plural = points_earned != 1 and 's' or ''
            self.status.append((STATUS_POINTS_EARNED, (points_earned, plural)))

    @classmethod
    def _calc_winning_paths(cls):
        """Set ``cls._winning_paths``.

        This is a list of winning paths, which themselves are lists of
        ``(x, y, z)`` tuples.  Each path is sorted so that the highest z
        is always in the first tuple.  This is so that you can quickly
        discover if you can skip the whole path.

        """
        paths = cls._winning_paths = []
        # tic-tac-toe within a level
        for z in RANGE_SIZE:
            for y in RANGE_SIZE:
                # Rows
                paths.append([(x, y, z) for x in RANGE_SIZE])
            for x in RANGE_SIZE:
                # Columns
                paths.append([(x, y, z) for y in RANGE_SIZE])
            # Diagonals
            paths.append([(i, i, z) for i in RANGE_SIZE])
            paths.append([(invert(i), i, z) for i in RANGE_SIZE])
        # tic-tac-toe across levels
        for x in RANGE_SIZE:
            for y in RANGE_SIZE:
                # Vertical lines
                paths.append([(x, y, z) for z in RANGE_SIZE_REVERSED])
            # Column stairs
            paths.append([(x, i, i) for i in RANGE_SIZE_REVERSED])
            paths.append([(x, invert(i), i) for i in RANGE_SIZE_REVERSED])
        for y in RANGE_SIZE:
            # Row stairs
            paths.append([(i, y, i) for i in RANGE_SIZE_REVERSED])
            paths.append([(invert(i), y, i) for i in RANGE_SIZE_REVERSED])
        # Diagonal stairs
        paths.append([(i, i, i) for i in RANGE_SIZE_REVERSED])
        paths.append([(i, invert(i), i) for i in RANGE_SIZE_REVERSED])
        paths.append([(invert(i), i, i) for i in RANGE_SIZE_REVERSED])
        paths.append([(invert(i), invert(i), i) for i in RANGE_SIZE_REVERSED])


class Square:

    """This represents the state of a single square on the board.

    The following properties are used:

    xyz
      This is the location of the square.

    value
      This is either BLANK, RED, or BLUE.

    special
      This is True if the square is a special square.

    """

    def __init__(self, xyz):
        """Which square am I?  Reset."""
        self.xyz = xyz
        self.reset()

    def __repr__(self):
        """Return a simple repr for a square."""
        return self.value + (self.special and SPECIAL or ' ')

    def reset(self):
        """Reset the values of the square."""
        self.value = BLANK
        self.special = False


class TextGame:

    """This is a text-version of the game."""

    def __init__(self):
        """Start the game."""
        self.game = Game()

    def run(self):
        """This is the game's main loop."""
        try:
            while True:
                print self.game
                self.print_status()
                if self.game.done:
                    print  # Newline after status.
                    break
                self.move()
                print
        except (EOFError, KeyboardInterrupt):
            pass

    def print_status(self):
        """Print out status to the user.

        Don't use a newline.

        """
        if not self.game.status:
            return 
        print ' '.join([fmt % args for (fmt, args) in self.game.status]),

    def move(self):
        """Ask the user to make a move.

        Validate it and then do it.

        """
        fmt = 'Expected num,num'
        print ('%s, please enter row,col:' % self.game.current_player),
        nums = raw_input().split(',')
        if len(nums) != 2:
            print fmt
            return self.move()
        try:
            nums = map(int, nums)
        except ValueError:
            print fmt
            return self.move()
        for num in nums:
            if num < 1 or 3 < num:
                print 'Out of range:', num
                return self.move()
        (row, col) = nums
        (x, y) = (col - 1, row - 1)
        try:
            self.game.move((x, y, self.game.current_level))
        except ValueError, e:
            print e.args[0]
            return self.move()


def invert(i):
    """This is ``SIZE - 1 - i``."""
    return SIZE - 1 - i


def main():
    """``TextGame().run()``"""
    TextGame().run()


if __name__ == '__main__':
    main()
