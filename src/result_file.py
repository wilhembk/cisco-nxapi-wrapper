import time

from enum import Enum
from src.utils import ANSI
from abc import ABC, abstractmethod
from typing import Dict, Tuple, cast, Any, List
from datetime import datetime

class Label(Enum):
    HOST_INFO = "host"
    UNUSED_PORTS = "unused"
    TRANSCEIVER = "transceiver"
    HALF_DUPLEX = "half_duplex"
    CRC_ALIGN = "crc_align"
    PTP = "ptp"
    ERR_DISABLED = "err_disabled"

# How to add a new type of monitoring output:

# 1. Add a new `Label` entry above corresponding to your monitoring.

# 2. Create a new class inheriting from `ResultOutput` implementing `write(self, output)`.
#    `write` receives a callable `output` that writes strings to the result file.
#    This callable is passed automatically by the commit function of the `ResultFile` class.
   
# 3. Add helper methods on `ResultFile` to initialise / update your object (see existing set_* methods)
#    Use `_init_dict(ip_addr)` to ensure the dict entry exists before assigning your output class:
#    `self.switch_outputs[ip_addr][<Label>] = YourOutputClass(...)`.

# 4. From your monitoring code (in `nxapi_requests.py`) call those `ResultFile`
#    helper methods to populate the result object as data is discovered.

# NOTE: As long as your output class is defined in the switch_output dictionary, the `commit()`` method 
# in `ResultFile` will write your output in the result file accordiing to your `write` method defined in step 2.
# This method is called by `main.py` at the end of all checks.


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
            output("There are no unused ports.\n\n")
            return
        
        output(f"> The following ports are unused since {self.unused_since} days\n")
        for port in self.port_list:
            output(f"\t- {port["readable_id"]}\n")

        if self.successful_down:
            output("Those ports are now administratively down. You will no longer be notified. Consider unplugging them.\n")
        else:
            output("Consider unplugging or disabling them to not be notified again.\n")
        output("\n")

class HalfDuplexIfaces(ResultOutput):
    def __init__(self, port_list):
        self.port_list = port_list

    def write(self, output):
        if len(self.port_list) == 0:
            output("There are no interfaces running in half duplex.\n\n")
            return
        
        output(f"> CRITICAL: The following interfaces are running in half duplex\n")
        for port in self.port_list:
            output(f"\t- {port["readable_id"]}\n")
        output("\n")

class ErrDisabledIfaces(ResultOutput):
    def __init__(self):
        self.ifaces: List[Tuple[str, str]] = [] # (readable-iface-name, error type)
    
    def write(self, output):
        if len(self.ifaces) == 0:
            output("There are no interfaces that are disabled due to an error\n\n")
            return
        
        output(f"> The following interfaces were down because of an operational error:\n")
        for iface, error in self.ifaces:
            output(f"\t- {iface} is down due to {error}\n")
        output("\n")

class TransceiverInfo(ResultOutput):

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
            output("There are no issues with the transceivers' hardware.\n\n")
            return

        output(f"> The following transceivers show hardware issues:\n")
        for ifaces, lanes in self.notification.items():
            output(f"\t- Interface: {ifaces}\n")
            
            if "all" in lanes.keys():
                # In NXAPI temperature and voltage details are inside a lane_number
                # But there are repeated (since they are note lane specific)
                # So they are stored in "all" instead of a specific lane in this case.
                if lanes["all"].get("temp", None) != None:
                    temp = lanes["all"]["temp"]
                    temp_threshold = lanes["all"]["temp_threshold"]
                    hi = (temp >= temp_threshold) # Check if the high threshold is reached, or if it's the low threshold

                    if lanes["all"]["status_temp"] == "WARN":
                        output(f"\t\t+ WARN: Transceiver temperature exceeded the threshold ! ({temp}°C {">" if hi else "<"} {temp_threshold}°C)\n") 
                    
                    if lanes["all"]["status_temp"] == "ALERT":
                        output(f"\t\t+ ALERT: Transceiver temperature exceeded the threshold ! ({temp}°C {">" if hi else "<"} {temp_threshold}°C)\n")

                if lanes["all"].get("voltage", None) != None:
                    voltage = lanes["all"]["voltage"]
                    voltage_threshold = lanes["all"]["voltage_threshold"]
                    hi = (voltage >= voltage_threshold) # Check if the high threshold is reached, or if it's the low threshold

                    if lanes["all"]["status_voltage"] == "WARN":
                        output(f"\t\t+ WARN: Transceiver voltage exceeded the threshold ! ({voltage} {">" if hi else "<"} {voltage_threshold})\n") 
                    
                    if lanes["all"]["status_voltage"] == "ALERT":
                        output(f"\t\t+ ALERT: Transceiver voltage exceeded the threshold ! ({voltage} {">" if hi else "<"} {voltage_threshold})\n")


                if lanes["all"].get("current", None) != None:
                    current = lanes["all"]["current"]
                    current_threshold = lanes["all"]["current_threshold"]
                    hi = (current >= current_threshold) # Check if the high threshold is reached, or if it's the low threshold

                    if lanes["all"]["status_current"] == "WARN":
                        output(f"\t\t+ WARN: Transceiver current exceeded the threshold ! ({current} {">" if hi else "<"} {current_threshold})\n") 
                    
                    if lanes["all"]["status_current"] == "ALERT":
                        output(f"\t\t+ ALERT: Transceiver current exceeded the threshold ! ({current} {">" if hi else "<"} {current_threshold})\n")

            
            for lane_number, status in lanes.items():
                
                if lane_number == "all":
                    # Ignoring transceiver global details.
                    continue


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

class cRCCounter(ResultOutput):

    def __init__(self, critical_delta: int):
        self.deltas: Dict[str, Tuple[int, int, int]] = {} # dn -> (delta, current_cRC, reference_cRC)
        self.critical_delta = critical_delta

    def write(self, output):

        if len(self.deltas) == 0:
            output("There are no additional cRC or Align errors compared to the last check\n\n")
            return
        
        output("> The following interfaces shows additional cRC or Align errors compared to the last check\n")
        for dn, values in self.deltas.items():
            delta, curr, ref = values

            if delta >= self.critical_delta:
                output(f"\t- CRITICAL: {dn} shows {delta} new errors ")
            else:
                output(f"\t- {dn} shows {delta} new errors ")
            
            if curr == delta and ref != 0:
                # The counter has been reseted between checks
                output(f"(now {curr}, was {ref} and reset since)\n")
            else:
                output(f"(now {curr}, was {ref})\n")
        output("\n")


class PTPInfoGlobal(ResultOutput):
    def __init__(self):
        self.gm_used: Dict[str, List[str]] = {}

    def add_clock(self, gm: str, clock: str):

        if gm not in self.gm_used.keys():
            self.gm_used[gm] = [clock]
            return
        
        self.gm_used[gm].append(clock)


    def write(self, output):
        gm_clocks = list(self.gm_used.keys())
        if len(gm_clocks) == 1:
            output(f"PTP: All switches are synced with the same Grandmaster clock: {gm_clocks[0]}\n\n")
            return
        
        output(f"> PTP: Switches have different Grandmaster clocks !\n")
        for clock in gm_clocks:
            output(f"\t- Grandmaster {clock} is synced with:\n")
            for switch in self.gm_used[clock]:
                output(f"\t\t+ {switch}\n")
        output("\n")


class PTPInfoLocal(ResultOutput):

    def __init__(self):
        """log_ptp :
        - 0 NEVER
        - 1 ONLY ON ERRORS
        - 2 ALWAYS
        """
        self.log_ptp = 0
        self.parent_mac = "00:00:00:00:00:00"
        self.clock_mac = "00:00:00:00:00:00"
        self.gm_mac = "00:00:00:00:00:00"
        self.critical_correction = 0
        self.gm_changes = []
        self.high_corrections = []
        self.logs = ""
    

    def write(self, output):
        if self.clock_mac == self.gm_mac:
            output(f"> This switch's clock {self.clock_mac} is Grandmaster\n")
        else:
            if self.parent_mac == self.gm_mac:
                output(f"> This switch's clock {self.clock_mac} is synced to Grandmaster clock {self.gm_mac} (directly connected)\n")
            else:
                output(f"> This switch's clock {self.clock_mac} is synced to Grandmaster clock {self.gm_mac} (via {self.parent_mac})\n")
        output("\n")

        gm_changed = len(self.gm_changes) != 0
        if gm_changed: 
            output(f"> This switch has changed Grandmaster clock recently:\n")

        for gm_change in self.gm_changes:
            date, mac_init, mac_dest = gm_change
            output(f"\t- {date.strftime("%a %d %b %Y, %I:%M")}: Changed GM from {mac_init} to {mac_dest}\n")
        if gm_changed: output("\n")

        abnormal_correction = len(self.high_corrections) != 0
        if abnormal_correction:
            output(f"> This switch reached abnormal correction times:\n")
        for hc in self.high_corrections:
            abnormal_correction = True
            iface = hc["intf-name"]
            suptime = hc["sup-time"]
            correction = hc["correction-val"]
            # Specify clock name !
            output(f"\t- CRITICAL at {suptime}: While on {iface} reached correction of {correction} ns ! ({correction} >= {self.critical_correction})\n")
        if abnormal_correction: output("\n")

        if self.log_ptp == 2 or (self.log_ptp == 1 and (gm_changed or abnormal_correction)):
            output(f"---------- Full PTP log ----------\n\n")
            output(self.logs)
            output(f"\n----------------------------------\n")
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

        if self.switch_outputs.get("all"):
            self._output("********** GLOBAL NOTIFICATION **********\n\n")
            for label in self.switch_outputs["all"].keys():
                if label == Label.HOST_INFO:
                    # We don't print the host info again
                    continue

                self.switch_outputs["all"][label].write(self._output)
            self._output("*****************************************\n\n")


        for ip_addr, output in self.switch_outputs.items():
            if ip_addr == "all":
                continue
            
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


    def init_err_disabled(self, ip_addr: str):
        self._init_dict(ip_addr)
        if Label.ERR_DISABLED not in self.switch_outputs[ip_addr].keys():
            self.switch_outputs[ip_addr][Label.ERR_DISABLED] = ErrDisabledIfaces()


    def add_err_disabled(self, ip_addr: str, iface: str, error: str):
       
        self.init_err_disabled(ip_addr)
        err_disabled_ifaces = cast(ErrDisabledIfaces, self.switch_outputs[ip_addr][Label.ERR_DISABLED])
        err_disabled_ifaces.ifaces.append((iface, error))


    # NOTE: Those are the simplest helper methods to populate your class output
    def set_half_duplex_ifaces(self, ip_addr, port_list):
        self._init_dict(ip_addr)
        self.switch_outputs[ip_addr][Label.HALF_DUPLEX] = HalfDuplexIfaces(port_list)   
        

    def set_hostinfo(self, ip_addr: str, hostname: str):
        self._init_dict(ip_addr)
        self.switch_outputs[ip_addr][Label.HOST_INFO] = HostInfo(ip_addr, hostname)


    def init_transceiver(self, ip_addr: str):
        self._init_dict(ip_addr)
        if Label.TRANSCEIVER not in self.switch_outputs[ip_addr].keys():
            self.switch_outputs[ip_addr][Label.TRANSCEIVER] = TransceiverInfo()

    def _init_set_lane(self, ip_addr: str, iface: str, lane_number: str):

        self.init_transceiver(ip_addr)

        transceiver_info = cast(TransceiverInfo, self.switch_outputs[ip_addr][Label.TRANSCEIVER])

        transceiver_info.init_interface_lane(iface, lane_number)
        return transceiver_info

    def set_lane_connected(self, ip_addr: str, iface: str, lane_number: str, connected: bool):

        transceiver_info = self._init_set_lane(ip_addr, iface, lane_number)
        transceiver_info.notification[iface][lane_number]["connected"] = connected


    def set_lane_tx(self, ip_addr: str, iface: str, lane_number: str, tx_pwr: float, tx_threshold: float, is_alert=False):
        
        transceiver_info = self._init_set_lane(ip_addr, iface, lane_number)
        transceiver_info.notification[iface][lane_number]["tx"] = tx_pwr
        transceiver_info.notification[iface][lane_number]["tx_threshold"] = tx_threshold
        transceiver_info.notification[iface][lane_number]["status_tx"] = "WARN" if not is_alert else "ALERT"


    def set_lane_rx(self, ip_addr: str, iface: str, lane_number: str, rx_pwr: float, rx_threshold: float, is_alert=False):
        
        transceiver_info = self._init_set_lane(ip_addr, iface, lane_number)
        transceiver_info.notification[iface][lane_number]["rx"] = rx_pwr
        transceiver_info.notification[iface][lane_number]["rx_threshold"] = rx_threshold
        transceiver_info.notification[iface][lane_number]["status_rx"] = "WARN" if not is_alert else "ALERT"

    def set_temp(self, ip_addr: str, iface: str, temp_pwr: float, temp_threshold: float, is_alert=False):
        
        transceiver_info = self._init_set_lane(ip_addr, iface, "all")
        transceiver_info.notification[iface]["all"]["temp"] = temp_pwr
        transceiver_info.notification[iface]["all"]["temp_threshold"] = temp_threshold
        transceiver_info.notification[iface]["all"]["status_temp"] = "WARN" if not is_alert else "ALERT"

    def set_voltage(self, ip_addr: str, iface: str, voltage_pwr: float, voltage_threshold: float, is_alert=False):
        
        transceiver_info = self._init_set_lane(ip_addr, iface, "all")
        transceiver_info.notification[iface]["all"]["voltage"] = voltage_pwr
        transceiver_info.notification[iface]["all"]["voltage_threshold"] = voltage_threshold
        transceiver_info.notification[iface]["all"]["status_voltage"] = "WARN" if not is_alert else "ALERT"


    def set_current(self, ip_addr: str, iface: str, current_pwr: float, current_threshold: float, is_alert=False):
        
        transceiver_info = self._init_set_lane(ip_addr, iface, "all")
        transceiver_info.notification[iface]["all"]["current"] = current_pwr
        transceiver_info.notification[iface]["all"]["current_threshold"] = current_threshold
        transceiver_info.notification[iface]["all"]["status_current"] = "WARN" if not is_alert else "ALERT"

    def init_cRC_delta(self, ip_addr: str, critical_delta: int):
        self._init_dict(ip_addr)
        if Label.CRC_ALIGN not in self.switch_outputs[ip_addr].keys():
            self.switch_outputs[ip_addr][Label.CRC_ALIGN] = cRCCounter(critical_delta)

    def set_cRC_delta(self, ip_addr: str, critical_delta: int, dn: str, delta: int, current_cRC: int, reference_cRC: int):
        """
        dn is parsed as "sys/intf/phys-[iface]/dbgEtherStats" where iface is extracted
        """
        if delta <= 0:
            return
        
        self.init_cRC_delta(ip_addr, critical_delta)

        iface = dn.lstrip("sys/intf/phys-[").rstrip("]/dbgEtherStats")
        
        cRC_counter = cast(cRCCounter, self.switch_outputs[ip_addr][Label.CRC_ALIGN])
        cRC_counter.deltas[iface] = (delta, current_cRC, reference_cRC)


    def set_ptp(self, ip_addr: str, log_ptp: None | int = None, clock_parent_and_gm: None | Tuple[str, str, str] = None,
                critical_correction: None | int = None, gm_changes: None | List[Tuple[datetime, str, str]] = None,
                high_corrections: None | List[Dict[str, str]] = None, logs: None | str = None):

        self._init_dict(ip_addr)
        self._init_dict("all") # For PTP global notification

        if Label.PTP not in self.switch_outputs[ip_addr].keys():
            self.switch_outputs[ip_addr][Label.PTP] = PTPInfoLocal()

        if Label.PTP not in self.switch_outputs["all"].keys():
            self.switch_outputs["all"][Label.PTP] = PTPInfoGlobal()

        local_info = cast(PTPInfoLocal, self.switch_outputs[ip_addr][Label.PTP])
        global_info = cast(PTPInfoGlobal, self.switch_outputs["all"][Label.PTP])

        if log_ptp != None:
            local_info.log_ptp = log_ptp

        if clock_parent_and_gm != None:
            clock, parent, gm = clock_parent_and_gm
            local_info.clock_mac = clock
            local_info.parent_mac = parent
            local_info.gm_mac = gm
            global_info.add_clock(gm, clock)

        if critical_correction != None:
            local_info.critical_correction = critical_correction

        if gm_changes != None:
            local_info.gm_changes = gm_changes
        
        if high_corrections != None:
            local_info.high_corrections = high_corrections

        if logs != None:
            local_info.logs = logs