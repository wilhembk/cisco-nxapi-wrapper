import requests
import json
import re
from glom import glom 
from typing import Dict
import urllib3
from src.utils import ANSI, Logger
from src.result_file import ResultFile
from datetime import datetime

# The certificate is self-signed. So we disable warnings.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) 



# How to add a new monitoring endpoint or CLI-based check ?

# - Prefer using NXCLI_REST as those calls are much quicker than CLI ones.
#   For a GET request, add a method on `NX_REST` that uses `self._get(<point>)` (it wraps the request neatly)
#   Parse the returned JSON (use glom for concise extraction)
#   Push results to `self.result` using an appropriate `ResultFile` setter (see `result_file.py`).

# - If you must run a CLI command:
#   Add a method on `NXCLI_API` that uses `self._wrap_cmd("<cli command>")` (it wraps the request neatly)
#   Parse the returned JSON (use glom for concise extraction)
#   Push results to `self.result` using an appropriate `ResultFile` setter (see `result_file.py`).

# - After adding the method here, expose it on `SwitchConnection` (see `switch_connection.py`) 
#   That way, `main.py` can call it

# - For offline testing, `--demo_path` expects a directory structure mirroring
#   the API paths used by the code (an example lives in `demo_json/`).


class NXCLI_API:

    def __init__(self, user_id: str, password: str, switch_ip: str, logger: Logger, result: ResultFile, demo_path: str | None = None, timeout: int = 90):
        self.user_id = user_id
        self.password = password
        self.demo_path = demo_path
        self.timeout = timeout
        self.logger = logger
        self.switch_ip = switch_ip
        self.result = result
        self.endpoint = f"https://{switch_ip}/ins"

    def _wrap_cmd(self, cmd: str, method: str = "cli"):
        """
        Wrap the cmd inside the payload to send to the switch.
        The cmd requires authentication on the switch for it to work
        """

        if self.demo_path != None:
            self.logger.log(f"Demo mode is activated. Fetching from local file {self.demo_path}/{self.switch_ip}/ins/{cmd.replace(" ", "_")}.json")

            try:
                f = open(f"{self.demo_path}/{self.switch_ip}/ins/{cmd.replace(" ", "_")}.json", "r")
            except:
                self.logger.log(f"Demo file {self.demo_path}/{self.switch_ip}/ins/{cmd.replace(" ", "_")}.json is not readable")
                return {}

            return json.load(f)


        myheaders={'content-type':'application/json-rpc'}
        payload=[
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": {
                "cmd": cmd,
                "version": 1
                },
                "id": 1
            }
        ]

        self.logger.log(f"Running command \"{cmd}\" via NXAPI-CLI")
        try:
            req = requests.post(
                self.endpoint,
                data=json.dumps(payload), 
                headers=myheaders,
                auth=(self.user_id,self.password),
                verify=False,
                timeout=self.timeout
            )
        except requests.exceptions.Timeout:
            self.logger.log(f"NXAPI-CLI timed out after {self.timeout} seconds at {self.endpoint}")
            return {}
        except:
            self.logger.log(f"Could not reach NXAPI-CLI at {self.endpoint}")
            return {}
        
        response = req.json()

        return response
    

    def get_transceiver_details(self):
        """Returns the details of the transceivers, filtered down to plugged ones"""

        data = self._wrap_cmd("show interface transceiver details")
        if data == {}:
            return []

        try:
            res = glom(data, "result.body.TABLE_interface.ROW_interface")
        except:
            self.logger.log("NXAPI returned incoherent results when checking for transceivers")
            return []

        return list(filter(lambda iface: iface["sfp"] == "present",  res))

    
    def check_for_tranceiver_alerts(self, filter_warn=False):
        self.logger.log(f"Checking for alerts in transceiver status...")
        transceivers = self.get_transceiver_details()

        self.result.init_transceiver(self.switch_ip) # Checking for ltransceivers ? Adding it to results

        for tran in transceivers:
            iface = tran["interface"]
            if "TABLE_lane" not in tran.keys():
                # No data
                continue

            lanes = tran["TABLE_lane"]["ROW_lane"]
            for lane in lanes:
                if "tx_pwr_alrm_hi" in lane.keys():
                    # This an optic cable
                    self.check_light_level_lane(iface, lane, filter_warn)
                if "temp_alrm_hi" in lane.keys():
                    self.check_temp(iface, lane, filter_warn)
                if "volt_alrm_hi" in lane.keys():
                    self.check_voltage(iface, lane, filter_warn)
                if "current_alrm_hi" in lane.keys():
                    self.check_current(iface, lane, filter_warn)


    def check_light_level_lane(self, iface, lane, filter_warn):

        lane_number = lane["lane_number"]

        if "tx_pwr" not in lane.keys():
            self.logger.log(f"No cable connected for lane {lane_number} in {iface} !")
            self.result.set_lane_connected(self.switch_ip, iface, lane_number, False)
            return

        tx_alrm_hi = float(lane["tx_pwr_alrm_hi"])
        tx_alrm_low = float(lane["tx_pwr_alrm_lo"])
        tx_warn_hi = float(lane["tx_pwr_warn_hi"])
        tx_warn_low = float(lane["tx_pwr_warn_lo"])
        tx = float(lane["tx_pwr"])

        if not (tx_alrm_low <= tx <= tx_alrm_hi):
            if tx <= tx_alrm_low:
                self.result.set_lane_tx(self.switch_ip, iface, lane_number, tx, tx_alrm_low, is_alert=True)
            else:
                self.result.set_lane_tx(self.switch_ip, iface, lane_number, tx, tx_alrm_hi, is_alert=True)
            return
        
        if not filter_warn and not (tx_warn_low <= tx <= tx_warn_hi):
            if tx <= tx_warn_low:
                self.result.set_lane_tx(self.switch_ip, iface, lane_number, tx, tx_warn_low)
            else:
                self.result.set_lane_tx(self.switch_ip, iface, lane_number, tx, tx_warn_hi)
            return

        

        rx_alrm_hi = float(lane["rx_pwr_alrm_hi"])
        rx_alrm_low = float(lane["rx_pwr_alrm_lo"])
        rx_warn_hi = float(lane["rx_pwr_warn_hi"])
        rx_warn_low = float(lane["rx_pwr_warn_lo"])
        rx = float(lane["rx_pwr"])

        if not (rx_alrm_low <= rx <= rx_alrm_hi):
            if rx <= rx_alrm_low:
                self.result.set_lane_rx(self.switch_ip, iface, lane_number, rx, rx_alrm_low, is_alert=True)
            else:
                self.result.set_lane_rx(self.switch_ip, iface, lane_number, rx, rx_alrm_hi, is_alert=True)
            return
        
        if not filter_warn and not (rx_warn_low <= rx <= rx_warn_hi):
            if rx <= rx_warn_low:
                self.result.set_lane_rx(self.switch_ip, iface, lane_number, rx, rx_warn_low)
            else:
                self.result.set_lane_rx(self.switch_ip, iface, lane_number, rx, rx_warn_hi)
            return

    def check_temp(self, iface, lane, filter_warn):

        temp_alrm_hi = float(lane["temp_alrm_hi"])
        temp_alrm_low = float(lane["temp_alrm_lo"])
        temp_warn_hi = float(lane["temp_warn_hi"])
        temp_warn_low = float(lane["temp_warn_lo"])
        temp = float(lane["temperature"])


        if not (temp_alrm_low <= temp <= temp_alrm_hi):
            if temp <= temp_alrm_low:
                self.result.set_temp(self.switch_ip, iface, temp, temp_alrm_low, is_alert=True)
            else:
                self.result.set_temp(self.switch_ip, iface, temp, temp_alrm_hi, is_alert=True)
            return
        
        if not filter_warn and not (temp_warn_low <= temp <= temp_warn_hi):
            if temp <= temp_warn_low:
                self.result.set_temp(self.switch_ip, iface, temp, temp_warn_low)
            else:
                self.result.set_temp(self.switch_ip, iface, temp, temp_warn_hi)

        
    def check_current(self, iface, lane, filter_warn):

        current_alrm_hi = float(lane["current_alrm_hi"])
        current_alrm_low = float(lane["current_alrm_lo"])
        current_warn_hi = float(lane["current_warn_hi"])
        current_warn_low = float(lane["current_warn_lo"])
        current = float(lane.get("current", 0))


        if not (current_alrm_low <= current <= current_alrm_hi):
            if current <= current_alrm_low:
                self.result.set_current(self.switch_ip, iface, current, current_alrm_low, is_alert=True)
            else:
                self.result.set_current(self.switch_ip, iface, current, current_alrm_hi, is_alert=True)
            return
        
        if not filter_warn and not (current_warn_low <= current <= current_warn_hi):
            if current <= current_warn_low:
                self.result.set_current(self.switch_ip, iface, current, current_warn_low)
            else:
                self.result.set_current(self.switch_ip, iface, current, current_warn_hi)

    
    
    def check_voltage(self, iface, lane, filter_warn):

        volt_alrm_hi = float(lane["volt_alrm_hi"])
        volt_alrm_low = float(lane["volt_alrm_lo"])
        volt_warn_hi = float(lane["volt_warn_hi"])
        volt_warn_low = float(lane["volt_warn_lo"])
        volt = float(lane["voltage"])


        if not (volt_alrm_low <= volt <= volt_alrm_hi):
            if volt <= volt_alrm_low:
                self.result.set_voltage(self.switch_ip, iface, volt, volt_alrm_low, is_alert=True)
            else:
                self.result.set_voltage(self.switch_ip, iface, volt, volt_alrm_hi, is_alert=True)
            return
        
        if not filter_warn and not (volt_warn_low <= volt <= volt_warn_hi):
            if volt <= volt_warn_low:
                self.result.set_voltage(self.switch_ip, iface, volt, volt_warn_low)
            else:
                self.result.set_voltage(self.switch_ip, iface, volt, volt_warn_hi)

    def _get_ptp_corrections(self):
        """Returns a list in chronological order showing ptp corrections"""
        try:
            res = glom(self._wrap_cmd("show ptp corrections"), "result.body.TABLE_ptp.ROW_ptp")
        except:
            res = []
        return res
    
    def _get_ptp_parent(self):
        data = self._wrap_cmd("show ptp parent")
        if data == {}:
            return {}

        try:
            return glom(data, "result.body")
        except:
            self.logger.log("NXAPI returned incoherent results when checking PTP parent")
            return {}
    
    def _get_clock_id(self):
        data = self._wrap_cmd("show ptp clock")
        if data == {}:
            return ""

        try:
            return glom(data, "result.body.clock-id")
        except:
            self.logger.log("NXAPI returned incoherent results when checking PTP clock")
            return ""
    

    def _get_ptp_logs(self):
        try:
            res = glom(self._wrap_cmd("show logging logfile | grep -i ptp", method="cli_ascii"), "result.msg")
        except:
            res = ""
        return res


    def get_critical_ptp_corrections(self, critical_correction: int):

        self.result.set_ptp(self.switch_ip, critical_correction=critical_correction)

        corrections = self._get_ptp_corrections()
        if len(corrections) == 0:
            # Surely a grandmaster.
            return 
        
        res = list(filter(lambda e: int(e["correction-val"]) >= critical_correction, corrections))
        res.reverse()
        self.result.set_ptp(self.switch_ip, high_corrections=res)

        return res

    def get_ptp_gm(self):
        clock_data = self._get_ptp_parent()
        if clock_data == {}:
            return None

        clock_id = self._get_clock_id()
        if clock_id == "":
            return None

        clock_parent_and_gm = clock_id, clock_data["clock-id"], clock_data["gm-id"]
        
        self.result.set_ptp(self.switch_ip, clock_parent_and_gm=clock_parent_and_gm)
        return clock_parent_and_gm

    def get_gm_change(self, log_level: int, since: int):
        # Grandmaster clock has changed {MAC_1} to {MAC_2}


        logs = self._get_ptp_logs()
        self.result.set_ptp(self.switch_ip, log_ptp=log_level, logs=logs)

        res = []    

        for line in logs.split("\n"):
            pattern = re.compile(r"(?P<date>\d{4}\s+[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}).*?Grandmaster clock has changed from (?P<mac_init>[0-9a-fA-F:]+) to (?P<mac_dest>[0-9a-fA-F:]+)")
            match = pattern.search(line)

            if not match:
                continue

            today = datetime.now()
            date_str = match.group("date")
            date = datetime.strptime(date_str, "%Y %b %d %H:%M:%S")

            delta = today - date
            if delta.days > since:
                continue
        
            res.append((date, match.group("mac_init"), match.group("mac_dest")))

        self.result.set_ptp(self.switch_ip, gm_changes=res)
        return res
    
    def check_ptp(self, since: int, log_level: int, critical_correction: int):
        self.get_ptp_gm()
        self.get_critical_ptp_corrections(critical_correction)
        self.get_gm_change(log_level, since)


class NXREST_API:

    def __init__(self, user_id: str, password: str, switch_ip: str, logger: Logger, result: ResultFile, demo_path: str | None = None, timeout: int = 90):
        """Call login to initialise the object auth cookies and start making requests"""
        self.user_id = user_id
        self.password = password
        self.switch_ip = switch_ip
        self.demo_path = demo_path
        self.timeout = timeout
        self.hostname = None
        self.serial = None
        self.api_url = f"https://{self.switch_ip}/api/"
        self.logger = logger
        self.result = result
        self.auth_cookie = {}


    def login(self):
        if self.demo_path != None:
            return True
            
        payload = {
            'aaaUser' : {
                'attributes' : {
                    'name' : self.user_id,
                    'pwd' : self.password,
                    }
                }
            }


        endpoint = self.api_url+"aaaLogin.json"

        self.logger.log(f"Login into {self.switch_ip} with the provided credentials. (POST: {endpoint})")


        try:
            response = requests.request("POST", endpoint, data=json.dumps(payload), verify=False, timeout=self.timeout)
        except requests.exceptions.Timeout:
            self.logger.log(f"Login into {self.switch_ip} timed out after {self.timeout} seconds")
            return False
        except:
            self.logger.log(f"The switch {self.switch_ip} is unreachable")
            return  False
        
        if response.status_code == requests.codes.ok:
            data = json.loads(response.text)['imdata'][0]
            token = str(data['aaaLogin']['attributes']['token'])
            self.auth_cookie = {"APIC-cookie" : token}
            self.logger.log(f"Logged into {self.switch_ip} successfully.")
            return True
              
        else:
            self.logger.log(f"Login into {self.switch_ip} failed. Are the credentials correct ? Ignoring this switch")
            return False

        
    
    def logout(self):
        """
        Close the connection gracefully
        """

        if self.demo_path != None:
            return

        payload = {
        'aaaUser' : {
            'attributes' : {
                'name' : self.user_id
                }
            }
        }
        endpoint = self.api_url+ "aaaLogout.json"
        try:
            requests.request("POST", endpoint, data=json.dumps(payload), cookies=self.auth_cookie, verify=False, timeout=self.timeout)
        except requests.exceptions.Timeout:
            self.logger.log(f"Logout from {self.switch_ip} timed out after {self.timeout} seconds")
        except:
            self.logger.log(f"Could not log out gracefully from {self.switch_ip}")

        self.logger.log(f"Successfully logged out from the switch {self.switch_ip}")
        self.auth_cookie = {}


    def _get(self, point: str):

        if self.demo_path:
            self.logger.log(f"Demo mode is activated. Fetching from local file {self.demo_path}/{self.switch_ip}/{point}")
            with open(f"{self.demo_path}/{self.switch_ip}/{point}", "r") as f:
                return json.load(f)
            self.logger.log(f"The file {self.demo_path}/{self.switch_ip}/{point} is unreadable")
            return {}
        
        if self.auth_cookie == {}:
            self.login()
        
        endpoint = f"{self.api_url}{point}"
        self.logger.log(f"GET {endpoint}")
        try:
            response = requests.request("GET", endpoint, cookies=self.auth_cookie, verify=False, timeout=self.timeout)
        except requests.exceptions.Timeout:
            self.logger.log(f"GET {endpoint} timed out after {self.timeout} seconds")
            return {}
        except:
            self.logger.log(f"Could not reach {endpoint}")
            return {}
        if response.status_code != requests.codes.ok:
            self.logger.log(f"The endpoint {endpoint} does not exist.")
            return {}
        return response.json()
    
    def _get_system(self):
        return self._get("mo/sys.json")

    def get_hostname_and_serial(self):
        if self.hostname != None:
            return self.hostname
        self.logger.log(f"Getting switch hostname and serial number")
        
        data = self._get_system()
        if data == {}:
            self.logger.log(f"Could not fetch hostname and serial for {self.switch_ip}.")
            return None, None

        try:
            self.hostname = glom(data, ("imdata", ["topSystem.attributes.name"]))[0]
            self.serial = glom(data, ("imdata", ["topSystem.attributes.serial"]))[0]
        except:
            self.logger.log(f"Could not parse hostname and serial for {self.switch_ip}")
            return None, None
        self.result.set_hostinfo(ip_addr=self.switch_ip, hostname=self.hostname, serial=self.serial)
        return self.hostname, self.serial



    def _get_faults(self):
        return self._get("class/faultInst.json")


    def _get_ifaces(self):
        return self._get("class/ethpmPhysIf.json")
    

    def get_ifaces_states(self, filter_admin_down=False, filter_absent=False) -> list:

        ifaces = self._get_ifaces()
        if ifaces == {}:
            return []

        keep = ("imdata",
                [{
                    "adminSt": "ethpmPhysIf.attributes.adminSt",
                    "dn": "ethpmPhysIf.attributes.dn",
                    "lastLinkStChg": "ethpmPhysIf.attributes.lastLinkStChg",
                    "operSt": "ethpmPhysIf.attributes.operSt",
                    "operStQual": "ethpmPhysIf.attributes.operStQual",
                    "operDuplex": "ethpmPhysIf.attributes.operDuplex",
                    "operErrDisQual": "ethpmPhysIf.attributes.operErrDisQual"
                }]
                )
        
        try:
            data = glom(ifaces, keep)
        except:
            self.logger.log("NXAPI returned incoherent interface results")
            return []
        if filter_admin_down:
            data = list(filter(lambda iface: iface["adminSt"].upper() != "DOWN", data))

        if filter_absent:
            data = list(filter(lambda iface: iface["operStQual"].upper() != "XCVR-ABSENT", data))


        for i in range(len(data)):
            data[i]["readable_id"] = data[i]["dn"].lstrip("sys/intf/phys-[").rstrip("]/phys") 
            # Show as "eth1/33" where 1 is the card number, and 33 the port number.

        return data


    def print_ifaces(self, filter_admin_down=False, filter_absent=False):
        """
        Print current interfaces state. Can filter out absent interfaces and interface
        down by an admin.
        """

        data = self.get_ifaces_states(filter_admin_down, filter_absent)

        for iface in data:

            s = iface["readable_id"]

            if iface["operStQual"].upper() == "XCVR-ABSENT":
                s += f"\t{ANSI.COLOR_YELLOW}{ANSI.STYLE_BOLD}unplugged{ANSI.RESET_ALL}\tis"
            else:
                s += f"\t{ANSI.COLOR_BLUE}{ANSI.STYLE_BOLD}plugged{ANSI.RESET_ALL}\t\tis"

            if iface["adminSt"].upper() == "DOWN":
                print(f"{s} {ANSI.COLOR_RED}{ANSI.STYLE_BOLD}DOWN{ANSI.RESET_ALL} by admin\tsince {iface["lastLinkStChg"]}")
                continue

            if iface["operSt"].upper() == "DOWN":
                s += f" {ANSI.COLOR_RED}{ANSI.STYLE_BOLD}DOWN{ANSI.RESET_ALL}\t\t\t"

            elif iface["operSt"].upper() == "UP":
                s += f" {ANSI.COLOR_GREEN}{ANSI.STYLE_BOLD}UP{ANSI.RESET_ALL}\t\t\t"

            else:
                s += f" {ANSI.COLOR_YELLOW}{ANSI.STYLE_BOLD}{iface["operSt"]}{ANSI.RESET_ALL}\t\t\t"

            print(f"{s}since {iface["lastLinkStChg"]}")


    def print_system_info(self):
        system = self._get_system()
        if system == {}:
            self.logger.log(f"Could not fetch system information for {self.switch_ip}.")
            return
        
        keep = ("imdata",
                [{
                    "currentTime": "topSystem.attributes.currentTime",
                    "name": "topSystem.attributes.name",
                    "uptime": "topSystem.attributes.systemUpTime"
                }])
        
        try:
            data = glom(system, keep)[0]
        except:
            self.logger.log(f"Could not parse system information for {self.switch_ip}.")
            return
        print(f"Hostname {data["name"]} - Current Time: {data["currentTime"]} - Uptime: {data["uptime"]}")



    def get_ifaces_down_since(self, days):
        self.logger.log(f"Looking for unused interface since {days} days...")
        data = self.get_ifaces_states(filter_admin_down=True)
        
        today = datetime.today()

        # We check all down interfaces in data
        unused_ports = []
        for iface in filter(lambda iface: iface["operSt"].upper() != "UP", data):
            # iface["laistLinkStChg"] = "YYYY-mm-ddTHH:MM:SS.ms+GMT"
            down_since = datetime.strptime(iface["lastLinkStChg"].split("T")[0], "%Y-%m-%d")
            down_days = (today - down_since).days
            if down_days < days:
                continue
            self.logger.log(f"{iface["readable_id"]} is down since {down_days} days")
            unused_ports.append(iface)
        
        self.result.set_unused_ports(ip_addr=self.switch_ip, port_list=unused_ports, unused_since=days)
        return unused_ports  
    
    def get_half_duplex(self):
        self.logger.log(f"Checking for interfaces in half duplex...")
        data = self.get_ifaces_states(filter_admin_down=True, filter_absent=True)

        half_duplex_ifaces = []
        for iface in filter(lambda iface: iface["operSt"].upper() != "DOWN", data):
            if iface["operDuplex"] == "half":
                self.logger.log(f"{iface["readable_id"]} is in half duplex !!!")
                half_duplex_ifaces.append(iface)

        self.result.set_half_duplex_ifaces(self.switch_ip, half_duplex_ifaces)
        return half_duplex_ifaces


    def get_ifaces_err_disabled(self):
        self.result.init_err_disabled(self.switch_ip)
        data = self.get_ifaces_states(filter_admin_down=True, filter_absent=True)

        err_disabled = list(filter(lambda iface: iface["operErrDisQual"].upper() != "UP", data))
        for iface in err_disabled:
            self.result.add_err_disabled(self.switch_ip, iface["readable_id"], iface["operErrDisQual"])
        return err_disabled

    def _post_interfaceEntity(self, children):

        if self.demo_path != None:
            return False

        headers = { "Content-Type": "application/json" }
        payload = {
            "interfaceEntity": {
                "children": children
            }
        }

        endpoint = self.api_url + "mo/sys.json"
        self.logger.log(f"POST {endpoint}: {payload}")
        try:
            res = requests.post(endpoint, cookies=self.auth_cookie, headers=headers, data=json.dumps(payload), verify=False, timeout=self.timeout)
        except requests.exceptions.Timeout:
            self.logger.log(f"POST {endpoint} timed out after {self.timeout} seconds")
            return False
        except:
            self.logger.log(f"Could not reach {endpoint}")
            return False
        if res.status_code != requests.codes.ok:
            self.logger.log(f"Request failed: {res.text}")
            return False
        return True
            


    def down_ifaces(self, ifaces):
        if len(ifaces) == 0:
            return

        children = [
            {
                "l1PhysIf": {
                    "attributes": {
                        "dn": iface["dn"].rstrip("/phys"),
                        "adminSt": "down"
                    }
                }

            }
            for iface in ifaces
        ] # Generating payload to post
        success = self._post_interfaceEntity(children)
        self.result.set_unused_ports(ip_addr=self.switch_ip, successful_down=success)
        if success:
            self.logger.log(f"Successfully disabled {[iface["readable_id"] for iface in ifaces]}")

    def _get_rmonEtherStats(self):
        return self._get("class/rmonEtherStats.json")


    def _get_parsed_rmonEtherStats(self) -> Dict[str, Dict[str, str]]:
        """
        Returns a nested dictionnary wich first key is the dn, and where the second key correspond to the all the stat associated to this interface.
        """
        rmonEtherStats = self._get_rmonEtherStats()
        if rmonEtherStats == {}:
            return {}
        if rmonEtherStats["totalCount"] == '0':
            return {}
        
        try:
            data = glom(rmonEtherStats, ("imdata", ["rmonEtherStats.attributes"]))
        except:
            self.logger.log("NXAPI returned incoherent results when checking RMON statistics")
            return {}
        
        return {
            d["dn"]: {
                k:v
                for k, v in d.items() if k != "dn"
            }
            for d in data
        }


    def get_cRCAlignErrors(self, critical_delta, ref_dir_path):

        data = self._get_parsed_rmonEtherStats()
        if len(data) == 0:
            return

        self.result.init_cRC_delta(self.switch_ip, critical_delta) # Checking for cRC ? Adding it to results
        ref_file_path = f"{ref_dir_path}/{self.switch_ip.replace('.', '_')}.json"
        f = None
        try:
            f = open(ref_file_path, "r")
        except:
            print(f"{ANSI.COLOR_RED}[ERROR] CRC Reference file {ref_file_path} is unreadable. Assuming no reference... {ANSI.RESET_ALL}")
            f = None

        ref_data = {}
        if f: 
            ref_data = json.load(f)

        for dn in data.keys():
            current_cRC = int(data[dn]["cRCAlignErrors"])
            ref_cRC= int(ref_data.get(dn, {}).get("cRCAlignErrors", 0))
            # We get with default value in case the reference data does not contain what we are looking for

            # Two scenarios:
            # If current >= ref then normal routine
            # If ref > current, the counter has been reset, so assume current is the delta
            delta = current_cRC - ref_cRC if current_cRC >= ref_cRC else current_cRC

            if delta > 0:
                self.result.set_cRC_delta(self.switch_ip, critical_delta, dn, delta, current_cRC, ref_cRC)

        if f:
            f.close()
        try:
            f = open(ref_file_path, "w")
            json.dump(data, f, indent="\t")
            f.close()
        except:
            print(f"{ANSI.COLOR_RED}[ERROR] CRC Reference file {ref_file_path} is unwritable. Will not write references {ANSI.RESET_ALL}")



    def _get_stp(self):
        return self._get("class/stpIf.json")
