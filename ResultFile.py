import time

from enum import Enum
from utils import ANSI

class Label(Enum):
    UNUSED_PORTS = "unused"

class UnusedPorts:
    def __init__(self, port_list, unused_since, successful_down):
        self.port_list = port_list if port_list != None else []
        self.unused_since = unused_since if unused_since != None else 0
        self.successful_down = successful_down if successful_down != None else False


class ResultFile: 


    def __init__(self, path: str):

        self.switch_outputs = {} # Dict[str, Dict[str, str]]
        # The first key is the switch hostname
        # The values is a dict where:
        #   - The key is the "output_type" on wich:
        #       - UNUSED_PORTS is a tuple: (port_list, unused_since, successful_down)
        #   - The value is what to write for this output
        # Using a dict instead of a list ensure the same conventional order for each results.

        self.log_dir_path = path
        lt = time.localtime()
        self.log_file_path = \
            f"{self.log_dir_path}/result_{lt.tm_year}_{lt.tm_mon}_{lt.tm_mday}_{lt.tm_hour}_{lt.tm_min}_{lt.tm_sec}.txt"
        
        self.f = None
        try:
           self.f = open(self.log_file_path, "w")
        except:
            print(f"{ANSI.COLOR_RED}[ERROR] Can't open result {self.log_file_path} file. Will output in stdout{ANSI.RESET_ALL}")
            self.f = None
        if self.f: self.f.close()


    def _init_dict(self, hostname: str):
        if hostname not in self.switch_outputs.keys():
            self.switch_outputs[hostname] = {}


    def _output(self, s: str):
        if self.f == None:
            print(s, end="")
            return
        if self.f.closed:
            self.f = open(self.log_file_path, "w")
        self.f.write(s)

    def _end(self):
        if self.f == None or self.f.closed: 
            return
        self.f.close()


    def commit(self):
        """
        Writes the ResultFile fully.
        """

        for hostname, output in self.switch_outputs.items():
            self._output(f"=============[ Switch: {hostname} ]=============\n\n")        
            for label in output.keys():
                match label:
                    case Label.UNUSED_PORTS:
                        self._write_unused(output[Label.UNUSED_PORTS])
                        
        
            self._output(f"================================================\n")

        self._end()

    def _write_unused(self, out: UnusedPorts):
        if len(out.port_list) == 0:
            self._output("Currently, there are no unused ports.\n")
            return
        
        self._output(f"> The following ports are unused since {out.unused_since} days")
        for port in out.port_list:
            self._output(f"\t- {port["readable_id"]}")

        if out.successful_down:
            self._output("Those ports are now administratively down. You will no longer be notified. Consider unplugging them.\n")
        else:
            self._output("Consider unplugging or disabling them to not be notified again.\n")
        self._output("\n")



    def set_unused_ports(self, hostname, port_list = None, unused_since = None, successful_down = None):

        self._init_dict(hostname)

        if Label.UNUSED_PORTS not in self.switch_outputs[hostname].keys():
            self.switch_outputs[hostname][Label.UNUSED_PORTS] = UnusedPorts(port_list, unused_since, successful_down)  
            return 
        
        if port_list != None:
            self.switch_outputs[hostname][Label.UNUSED_PORTS].port_list = port_list
        if unused_since != None:
            self.switch_outputs[hostname][Label.UNUSED_PORTS].unused_since = unused_since
        if successful_down != None:
            self.switch_outputs[hostname][Label.UNUSED_PORTS].successful_down = successful_down

