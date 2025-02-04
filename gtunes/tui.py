import curses
from gtunes.db import init_db
from curses.textpad import Textbox, rectangle


def tui(stdscr):
    init_db()

    # curses passes things in y, x order :///
    stdscr.addstr(0, 0, "Enter tune name")

    editwin = curses.newwin(5,30, 2,1)
    rectangle(stdscr, 1,0, 1+5+1, 1+30+1)
    stdscr.refresh()

    box = Textbox(editwin)

    # Let the user edit until Ctrl-G is struck.
    box.edit()

    # Get resulting contents
    message = box.gather()
