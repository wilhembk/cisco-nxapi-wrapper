import sys
import time

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


class Logger:

    log_dir_path = ""
    log_file_path = ""

    def __init__(self, path: str):
        self.log_dir_path = path
        lt = time.localtime()
        self.log_file_path = \
            f"{self.log_dir_path}/log_{lt.tm_year}_{lt.tm_mon}_{lt.tm_mday}_{lt.tm_hour}_{lt.tm_min}_{lt.tm_sec}.log"
        
        f = None
        try:
           f = open(self.log_file_path, "w")
        except:
            print(f"{ANSI.COLOR_RED}[ERROR] Can't open log {self.log_file_path} file. Will log in stdout{ANSI.RESET_ALL}")
            self.log_file_path = ""
        if f: f.close()


    def log(self, msg):

        log_msg = f"{time.strftime("[%a, %d %b %Y %H:%M:%S]", time.localtime())} {msg}"
        if self.log_file_path == "":
            # No logs files. We print in stdout
            print(log_msg)
            return

        with open(self.log_file_path, "a") as f:
            f.write(log_msg+"\n")


class ResultFile: 


    def __init__(self, path: str):
        self.log_dir_path = path
        lt = time.localtime()
        self.log_file_path = \
            f"{self.log_dir_path}/result_{lt.tm_year}_{lt.tm_mon}_{lt.tm_mday}_{lt.tm_hour}_{lt.tm_min}_{lt.tm_sec}.txt"
        
        f = None
        try:
           f = open(self.log_file_path, "w")
        except:
            print(f"{ANSI.COLOR_RED}[ERROR] Can't open result {self.log_file_path} file. Will output in stdout{ANSI.RESET_ALL}")
            self.log_file_path = ""
        if f: f.close()

    def output(self, msg):
        if self.log_file_path == "":
            # No logs files. We print in stdout
            print(msg)
            return

        with open(self.log_file_path, "a") as f:
            f.write(msg+"\n")


    def begin_switch_result(self, hostname):
        self.output(f"=============[ Switch: {hostname} ]=============\n")


    def end_switch_result(self):
        self.output(f"================================================\n")


    def unused_ports(self, unused_since, port_list):
        if len(port_list) == 0:
            self.output("Currently, there are no unused ports.\n")
            return
        
        self.output(f"> The following ports are unused since {unused_since} days")
        for port in port_list:
            self.output(f"\t- {port}")
        self.output(f"Those ports are now administratively down. You will no longer be notified. Consider unplugging them.\n")
