import sys

class ANSI():
    RESET_ALL = "\x1b[0m" if sys.stdout.isatty() else ""
    COLOR_BLACK = "\x1b[30m" if sys.stdout.isatty() else ""
    COLOR_RED =  "\x1b[31m" if sys.stdout.isatty() else ""
    COLOR_GREEN = "\x1b[32m" if sys.stdout.isatty() else ""
    COLOR_YELLOW = "\x1b[33m" if sys.stdout.isatty() else ""
    COLOR_BLUE = "\x1b[34m" if sys.stdout.isatty() else ""
    COLOR_MAGENTA = "\x1b[35m" if sys.stdout.isatty() else ""
    COLOR_CYAN = "\x1b[36m" if sys.stdout.isatty() else ""
    COLOR_WHITE = "\x1b[37m" if sys.stdout.isatty() else ""

    BACKGROUND_BLACK ="\x1b[40m" if sys.stdout.isatty() else ""
    BACKGROUND_RED = "\x1b[41m" if sys.stdout.isatty() else ""
    BACKGROUND_GREEN = "\x1b[42m" if sys.stdout.isatty() else ""
    BACKGROUND_YELLOW = "\x1b[43m" if sys.stdout.isatty() else ""
    BACKGROUND_BLUE = "\x1b[44m" if sys.stdout.isatty() else ""
    BACKGROUND_MAGENTA = "\x1b[45m" if sys.stdout.isatty() else ""
    BACKGROUND_CYAN = "\x1b[46m" if sys.stdout.isatty() else ""
    BACKGROUND_WHITE = "\x1b[47m" if sys.stdout.isatty() else ""

    STYLE_BOLD = "\x1b[1m" if sys.stdout.isatty() else ""
    STYLE_ITALIC = "\x1b[3m" if sys.stdout.isatty() else ""
    STYLE_UNDERLINE = "\x1b[4m" if sys.stdout.isatty() else ""