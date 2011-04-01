"""This is home to the Scheduler class.

There's a singleton instance called "scheduler".

"""

import pygame

__docformat__ = 'restructuredtext'


class Scheduler:

    """Register callbacks to be called after a certain amount of time.

    This is the equivalent of Javascript's setTimer function.  I'm surprised
    PyGame doesn't have this, but I wasn't able to find it.

    The following attributes are used:

    waiting
      This is a list of tuples ``(ticks, callback)``.  I could
      get fancy with keeping the list in order like a kernel does, but
      it's just not worth the effort at this point.

    """

    def __init__(self):
        """Initialize."""
        self.waiting = []

    def tick(self):
        """You should call this on every frame.

        It'll call the callbacks.

        """
        now = pygame.time.get_ticks()
        # You can't modify a list you're looping over.
        to_call = [(ticks, callback)
                   for (ticks, callback) in self.waiting
                        if now >= ticks]
        for (ticks, callback) in to_call: 
            self.waiting.remove((ticks, callback))
            callback()

    def set_timer(self, milliseconds, callback):
        """Set a timer to call callback once after so many milliseconds.

        If milliseconds is set to 0, I'll remove the callback from the
        queue.

        """
        if milliseconds == 0:
            to_remove = [(ticks_, callback_)
                         for (ticks_, callback_) in self.waiting
                             if callback_ == callback]
            for (ticks_, callback_) in to_remove:
                self.waiting.remove((ticks_, callback_))
        else:
            now = pygame.time.get_ticks()
            self.waiting.append((now + milliseconds, callback))


scheduler = Scheduler()
