
import sys
import time
from glom import glom

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
        
        self.f = None
        try:
           self.f = open(self.log_file_path, "w")
        except:
            print(f"{ANSI.COLOR_RED}[ERROR] Can't open log {self.log_file_path} file. Will log in stdout{ANSI.RESET_ALL}")
            self.log_file_path = ""


    def log(self, msg):

        log_msg = f"{time.strftime('[%a, %d %b %Y %H:%M:%S]', time.localtime())} {msg}"
        if self.log_file_path == "" or self.f == None:
            # No logs files. We print in stdout
            print(log_msg)
            return
        
        self.f.write(log_msg+"\n")

    def end(self):
        if not self.f:
            return
        self.f.close()


def down_ifaces(ifaces, auto_down, sw, ndfc_conn, logger):
                
    if auto_down == 1:
        sw.down_ifaces(ifaces)
    
    if auto_down == 2:
        if ndfc_conn == None or not ndfc_conn.working_connection:
            logger.log("Tried to down interfaces via NDFC, but connection was not established.")
            return

        ports = glom(ifaces, ["readable_id"])
        ndfc_conn.shut_ports(sw.switch_ip, sw.serial, ports)

    if auto_down == 3:
        if ndfc_conn == None or not ndfc_conn.working_connection:
            logger.log("Tried to down interfaces via NDFC, but connection was not established.")
            return
        
        if ndfc_conn.is_managed_by_ndfc(sw.serial) == None:
            logger.log(f"Could not determined if {sw.serial} is managed on NDFC. Doing nothing.")
            return
        
        if ndfc_conn.is_managed_by_ndfc(sw.serial) == False:
            sw.down_ifaces(ifaces)
            return 

        ports = glom(ifaces, ["readable_id"])
        ndfc_conn.shut_ports(sw.switch_ip, sw.serial, ports)