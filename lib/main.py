"""This is the game's main module.

It contains the entry point used by the run_game.py script.

"""

import os.path
import sys
import webbrowser

import pygame
from pygame.locals import *

import data
import model
from scheduler import scheduler
import view

__docformat__ = 'restructuredtext'

TITLE = "TicTacToe3"
DISPLAY_MODE = (view.SCREEN_WIDTH, view.SCREEN_HEIGHT)
FRAMES_PER_SEC = 30
BACKGROUND = (0, 0, 0)


def main():

    """This is the entry point to the application."""

    # This is for text mode.

    if len(sys.argv) == 2 and sys.argv[1] == '-t':
        model.main()
        sys.exit(0)

    # Do initialization.

    pygame.init()
    screen = pygame.display.set_mode(DISPLAY_MODE)
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    background = pygame.Surface(screen.get_size()).convert()
    background.fill(BACKGROUND)
    pygame.display.flip()

    game_model = model.Game()
    board_view = view.Board(game_model)
    score_board = view.ScoreBoard(game_model)
    rendering_groups = [board_view, score_board]

    while True:

        clock.tick(FRAMES_PER_SEC)
        scheduler.tick()

        # Handle user input.

        for event in pygame.event.get():
            if event.type == KEYDOWN:
                if event.key in (K_ESCAPE, K_q) or event.type == QUIT:
                    sys.exit(0)
                elif event.key == K_h:
                    url = "file://" + os.path.abspath(data.find("help.html"))
                    webbrowser.open(url, new=True)
                elif event.key == K_r:
                    game_model.reset()
            elif event.type == MOUSEBUTTONDOWN:
                for square_view in board_view:
                    if square_view.rect.collidepoint(*pygame.mouse.get_pos()):
                        xyz = square_view.square_model.xyz
                        try:
                            game_model.move(xyz)
                        except ValueError:
                            pass
                        break

        # Provide the simulation and render it.

        for i in rendering_groups:
            i.update()
            i.clear(screen, background)
            pygame.display.update(i.draw(screen))
