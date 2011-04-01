"""Simple data loader module.

Loads data files from the "data" directory shipped with a game.

Enhancing this to handle caching, etc. is left as an exercise for the reader.

"""

import os

import pygame

__docformat__ = 'restructuredtext'

dirname = os.path.dirname(__file__)


def find(filename):
    """Given a filename, return a useable path for it."""
    return os.path.join(dirname, '..', 'data', filename)


def load(filename):
    """Find and open the given filename in binary mode."""
    return open(find(filename), 'rb')


def load_image(filename):
    """Find, load, and return an image.  Handle caching.

    Setup the alpha channel, if appropriate.

    """
    if filename not in load_image.cache:
        image = pygame.image.load(find(filename))
        if image.get_alpha() is None:
            image = image.convert()
        else:
            image = image.convert_alpha()
        load_image.cache[filename] = image
    return load_image.cache[filename]

load_image.cache = {}
