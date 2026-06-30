from enum import Enum

class ANSI:
    RESET_ALL = "\x1b[0m"
    COLOR_BLACK = "\x1b[30m"
    COLOR_RED =  "\x1b[31m"
    COLOR_GREEN = "\x1b[32m"
    COLOR_YELLOW = "\x1b[33m"
    COLOR_BLUE = "\x1b[34m"
    COLOR_MAGENTA = "\x1b[35m"
    COLOR_CYAN = "\x1b[36m"
    COLOR_WHITE = "\x1b[37m"

    BACKGROUND_BLACK ="\x1b[40m"
    BACKGROUND_RED = "\x1b[41m"
    BACKGROUND_GREEN = "\x1b[42m"
    BACKGROUND_YELLOW = "\x1b[43m"
    BACKGROUND_BLUE = "\x1b[44m"
    BACKGROUND_MAGENTA = "\x1b[45m"
    BACKGROUND_CYAN = "\x1b[46m"
    BACKGROUND_WHITE = "\x1b[47m"

    STYLE_BOLD = "\x1b[1m"
    STYLE_ITALIC = "\x1b[3m"
    STYLE_UNDERLINE = "\x1b[4m"