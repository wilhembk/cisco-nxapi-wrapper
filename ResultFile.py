import time

from enum import Enum
from utils import ANSI
from abc import ABC, abstractmethod
from typing import Dict, cast

class Label(Enum):
    UNUSED_PORTS = "unused"


class ResultOutput(ABC):
    @abstractmethod
    def write(self, output):
        pass


class UnusedPorts(ResultOutput):
    def __init__(self, port_list, unused_since, successful_down):
        self.port_list = port_list if port_list != None else []
        self.unused_since = unused_since if unused_since != None else 0
        self.successful_down = successful_down if successful_down != None else False

    def write(self, output):
        if len(self.port_list) == 0:
            output("Currently, there are no unused ports.\n")
            return
        
        output(f"> The following ports are unused since {self.unused_since} days")
        for port in self.port_list:
            output(f"\t- {port["readable_id"]}")

        if self.successful_down:
            output("Those ports are now administratively down. You will no longer be notified. Consider unplugging them.\n")
        else:
            output("Consider unplugging or disabling them to not be notified again.\n")
        output("\n")



class ResultFile: 


    def __init__(self, path: str):

        self.switch_outputs: Dict[str, Dict[Label, ResultOutput]] = {}
        # The first key is the switch hostname
        # The values is a dict where:
        #   - The key is the "output_type" on wich:
        #       - UNUSED_PORTS is a tuple: (port_list, unused_since, successful_down)
        #   - The value is what to write for this output
        # Using a dict helps set variables out of order.

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
                output[label].write(self._output)
                        
            self._output(f"================================================\n")

        self._end()


    def set_unused_ports(self, hostname, port_list = None, unused_since = None, successful_down = None):

        self._init_dict(hostname)

        if Label.UNUSED_PORTS not in self.switch_outputs[hostname].keys():
            self.switch_outputs[hostname][Label.UNUSED_PORTS] = UnusedPorts(port_list, unused_since, successful_down)  
            return 
        
        
        unused_ports = cast(UnusedPorts, self.switch_outputs[hostname][Label.UNUSED_PORTS])

        if port_list != None:
            unused_ports.port_list = port_list
        if unused_since != None:
            unused_ports.unused_since = unused_since
        if successful_down != None:
            unused_ports.successful_down = successful_down

