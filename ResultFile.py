import time

from enum import Enum
from utils import ANSI
from abc import ABC, abstractmethod
from typing import Dict, cast, Any

class Label(Enum):
    HOST_INFO = "host"
    UNUSED_PORTS = "unused"
    LIGHT_LEVEL = "light_level"

class NotificationLevel(Enum):
    NO_CABLE = "no_cable"
    INFO = "info"
    WARN = "warn"
    ALERT = "alert"

class ResultOutput(ABC):
    @abstractmethod
    def write(self, output):
        pass


class HostInfo(ResultOutput):
    def __init__(self, ip_addr: str, hostname: str):
        self.ip_addr = ip_addr
        self.hostname = hostname
    
    def write(self, output):
        output(f"=============[ Switch: {self.hostname} ({self.ip_addr}) ]=============\n\n") 


class UnusedPorts(ResultOutput):
    def __init__(self, port_list, unused_since, successful_down):
        self.port_list = port_list if port_list != None else []
        self.unused_since = unused_since if unused_since != None else 0
        self.successful_down = successful_down if successful_down != None else False

    def write(self, output):
        if len(self.port_list) == 0:
            output("Currently, there are no unused ports.\n\n")
            return
        
        output(f"> The following ports are unused since {self.unused_since} days")
        for port in self.port_list:
            output(f"\t- {port["readable_id"]}")

        if self.successful_down:
            output("Those ports are now administratively down. You will no longer be notified. Consider unplugging them.\n")
        else:
            output("Consider unplugging or disabling them to not be notified again.\n")
        output("\n")

class LightLevel(ResultOutput):

    def __init__(self):
        self.notification: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # Key 1: ifaces
        # Key 2: lane
        # Key 3: 
        #   connected: True/False
        #   status_tx: WARN, ALERT
        #   tx: <value>
        #   tx_threshold: <value exceeded>
        #   status_rx: WARN, ALERT
        #   rx: <value>
        #   rx_threshold: <value exceeded>


    def init_interface_lane(self, iface: str, lane_number: str):
        if iface not in self.notification.keys():
            self.notification[iface] = {lane_number: {}}
            return
        
        if lane_number in self.notification[iface].keys():
            return
        
        self.notification[iface][lane_number] = {}
        


    def write(self, output):

        if(len(self.notification) == 0):
            output("There are no issues with light levels in optical cables.\n\n")
            return


        output(f"> The following interfaces show optical hardware issues:\n")
        for ifaces, lanes in self.notification.items():
            output(f"\t- Interface: {ifaces}\n")
            for lane_number, status in lanes.items():
                if not status.get("connected", True):
                    output(f"\t\t+ CRITICAL: Lane {lane_number} is not plugged in !!!\n")
                    continue

                if status.get("tx", None) != None:
                    tx = status["tx"]
                    tx_threshold = status["tx_threshold"]
                    hi = (tx >= tx_threshold) # Check if the high threshold is reached, or if it's the low threshold

                    if status["status_tx"] == "WARN":
                        output(f"\t\t+ WARN: Lane {lane_number} transfer power has exceeded the threshold ! ({tx} {">" if hi else "<"} {tx_threshold})\n") 
                    
                    if status["status_tx"] == "ALERT":
                        output(f"\t\t+ ALERT: Lane {lane_number} transfer power has exceeded the threshold ! ({tx} {">" if hi else "<"} {tx_threshold})\n") 

                if status.get("rx", None) != None:
                    rx = status["rx"]
                    rx_threshold = status["rx_threshold"]
                    hi = (rx >= rx_threshold) # Check if the high threshold is reached, or if it's the low threshold

                    if status["status_rx"] == "WARN":
                        output(f"\t\t+ WARN: Lane {lane_number} receive power has exceeded the threshold ! ({rx} {">" if hi else "<"} {rx_threshold})\n") 
                    
                    if status["status_rx"] == "ALERT":
                        output(f"\t\t+ ALERT: Lane {lane_number} receive power has exceeded the threshold ! ({rx} {">" if hi else "<"} {rx_threshold})\n") 
            output("\n")
        output("\n")


class ResultFile: 


    def __init__(self, path: str):

        self.switch_outputs: Dict[str, Dict[Label, ResultOutput]] = {}
        # The first key is the switch ip_addr
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


    def _init_dict(self, ip_addr: str):
        if ip_addr not in self.switch_outputs.keys():
            self.switch_outputs[ip_addr] = {}


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

        for ip_addr, output in self.switch_outputs.items():
            
            if Label.HOST_INFO in output.keys():
                output[Label.HOST_INFO].write(self._output)
            else:
                self._output(f"=============[ Switch: {ip_addr} ]=============\n\n")

            for label in output.keys():
                if label == Label.HOST_INFO:
                    # We don't print the host info again
                    continue

                output[label].write(self._output)
                        
            self._output(f"================================================\n\n")

        self._end()


    def set_unused_ports(self, ip_addr, port_list = None, unused_since = None, successful_down = None):

        self._init_dict(ip_addr)

        if Label.UNUSED_PORTS not in self.switch_outputs[ip_addr].keys():
            self.switch_outputs[ip_addr][Label.UNUSED_PORTS] = UnusedPorts(port_list, unused_since, successful_down)  
            return 
        
        
        unused_ports = cast(UnusedPorts, self.switch_outputs[ip_addr][Label.UNUSED_PORTS])

        if port_list != None:
            unused_ports.port_list = port_list
        if unused_since != None:
            unused_ports.unused_since = unused_since
        if successful_down != None:
            unused_ports.successful_down = successful_down

    def set_hostinfo(self, ip_addr: str, hostname: str):
        self._init_dict(ip_addr)
        self.switch_outputs[ip_addr][Label.HOST_INFO] = HostInfo(ip_addr, hostname)


    def _init_set_lane(self, ip_addr: str, iface: str, lane_number: str):
        self._init_dict(ip_addr)
        if Label.LIGHT_LEVEL not in self.switch_outputs[ip_addr].keys():
            self.switch_outputs[ip_addr][Label.LIGHT_LEVEL] = LightLevel()

        light_level = cast(LightLevel, self.switch_outputs[ip_addr][Label.LIGHT_LEVEL])

        light_level.init_interface_lane(iface, lane_number)
        return light_level

    def set_lane_connected(self, ip_addr: str, iface: str, lane_number: str, connected: bool):

        light_level = self._init_set_lane(ip_addr, iface, lane_number)
        light_level.notification[iface][lane_number]["connected"] = connected


    def set_lane_tx(self, ip_addr: str, iface: str, lane_number: str, tx_pwr: float, tx_threshold: float, is_alert=False):
        
        light_level = self._init_set_lane(ip_addr, iface, lane_number)
        light_level.notification[iface][lane_number]["tx"] = tx_pwr
        light_level.notification[iface][lane_number]["tx_threshold"] = tx_threshold
        light_level.notification[iface][lane_number]["status_tx"] = "WARN" if not is_alert else "ALERT"


    def set_lane_rx(self, ip_addr: str, iface: str, lane_number: str, rx_pwr: float, rx_threshold: float, is_alert=False):
        
        light_level = self._init_set_lane(ip_addr, iface, lane_number)
        light_level.notification[iface][lane_number]["rx"] = rx_pwr
        light_level.notification[iface][lane_number]["rx_threshold"] = rx_threshold
        light_level.notification[iface][lane_number]["status_rx"] = "WARN" if not is_alert else "ALERT"


