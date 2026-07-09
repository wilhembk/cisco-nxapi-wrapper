import requests
import json
from glom import glom 
from typing import Dict
import urllib3
from utils import ANSI, Logger
from ResultFile import ResultFile
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class NXCLI_API:

    def __init__(self, user_id: str, password: str, switch_ip: str, logger: Logger, result: ResultFile):
        self.user_id = user_id
        self.password = password
        self.logger = logger
        self.switch_ip = switch_ip
        self.result = result
        self.endpoint = f"https://{switch_ip}/ins"

    def _wrap_cmd(self, cmd: str):
        """
        Wrap the cmd inside the payload to send to the switch.
        The cmd requires authentication on the switch for it to work
        """
        myheaders={'content-type':'application/json-rpc'}
        payload=[
            {
                "jsonrpc": "2.0",
                "method": "cli",
                "params": {
                "cmd": cmd,
                "version": 1
                },
                "id": 1
            }
        ]

        self.logger.log(f"Running command \"{cmd}\" via NXAPI-CLI")
        response = requests.post(
            self.endpoint,
            data=json.dumps(payload), 
            headers=myheaders,
            auth=(self.user_id,self.password),
            verify=False
        ).json()

        return response
    

    def get_hostname(self):
        return glom(self._wrap_cmd("show switchname"), "result.body.hostname")
    
    def save_config(self):
        return self._wrap_cmd("copy running-config startup-config")
    

    def get_transceiver_details(self):
        """Returns the details of the transceivers, filtered down to plugged ones"""

        with open("example_transceiver_details.json", "r") as f:
            return list(filter(
                    lambda iface: iface["sfp"] == "present", 
                    glom(json.load(f), "result.body.TABLE_interface.ROW_interface")))
    
    # self._wrap_cmd("show interface transceiver details")
    
    def check_for_tranceiver_alerts(self, filter_warn=False):
        # Check for duplex
        self.logger.log(f"Checking for alerts in transceiver status...")
        transceivers = self.get_transceiver_details()

        self.result.init_transceiver(self.switch_ip) # Checking for ltransceivers ? Adding it to results

        for tran in transceivers:
            iface = tran["interface"]
            if "TABLE_lane" not in tran.keys():
                # No data
                continue

            lanes = tran["TABLE_lane"]["ROW_lane"]
            temp_set = False
            for lane in lanes:
                if "tx_pwr_alrm_hi" in lane.keys():
                    # This an optic cable
                    self.check_light_level_lane(iface, lane, filter_warn)
                if "temp_alrm_hi" in lane.keys() and not temp_set:
                    temp_set = True
                    self.check_temp(iface, lane, filter_warn)
            temp_set = False


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

    def check_temp(self, iface, lane, filter_warn) -> bool:


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
            return True
        
        if not filter_warn and not (temp_warn_low <= temp <= temp_warn_hi):
            if temp <= temp_warn_low:
                self.result.set_temp(self.switch_ip, iface, temp, temp_warn_low)
            else:
                self.result.set_temp(self.switch_ip, iface, temp, temp_warn_hi)
            return True
        
        return False

class NXREST_API:

    def __init__(self, user_id: str, password: str, switch_ip: str, logger: Logger, result: ResultFile):
        """Call login to initialise the object auth cookies and start making requests"""
        self.user_id = user_id
        self.password = password
        self.switch_ip = switch_ip
        self.hostname = None
        self.api_url = f"https://{self.switch_ip}/api/"
        self.logger = logger
        self.result = result
        self.auth_cookie = {}


    def login(self):
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

        response = requests.request("POST", endpoint, data=json.dumps(payload), verify=False)
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
        payload = {
        'aaaUser' : {
            'attributes' : {
                'name' : self.user_id
                }
            }
        }
        endpoint = self.api_url+ "aaaLogout.json"
        requests.request("POST", endpoint, data=json.dumps(payload), cookies=self.auth_cookie, verify=False)
        self.auth_cookie = {}


    def _get(self, point: str):
        
        if self.auth_cookie == {}:
            self.login()
        
        endpoint = f"{self.api_url}{point}"
        self.logger.log(f"GET {endpoint}")
        response = requests.request("GET", endpoint, cookies=self.auth_cookie, verify=False)
        if response.status_code != requests.codes.ok:
            self.logger.log(f"The endpoint {endpoint} does not exist.")
            return {}
        return response.json()
    
    def _get_system(self):
        return self._get("mo/sys.json")

    def get_hostname(self):
        if self.hostname != None:
            return self.hostname
        self.logger.log(f"Getting switch hostname")
        self.hostname = glom(self._get_system(), ("imdata", ["topSystem.attributes.name"]))[0]
        self.result.set_hostinfo(ip_addr=self.switch_ip, hostname=self.hostname)
        return self.hostname


    def _get_faults(self):
        return self._get("class/faultInst.json")


    def _get_ifaces(self):
        return self._get("class/ethpmPhysIf.json")
    

    def get_ifaces_states(self, filter_admin_down=False, filter_absent=False) -> list:

        ifaces = self._get_ifaces()

        keep = ("imdata",
                [{
                    "adminSt": "ethpmPhysIf.attributes.adminSt",
                    "dn": "ethpmPhysIf.attributes.dn",
                    "lastLinkStChg": "ethpmPhysIf.attributes.lastLinkStChg",
                    "operSt": "ethpmPhysIf.attributes.operSt",
                    "operStQual": "ethpmPhysIf.attributes.operStQual",
                    "operDuplex": "ethpmPhysIf.attributes.operDuplex"
                }]
                )
        
        data = glom(ifaces, keep)
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
        
        keep = ("imdata",
                [{
                    "currentTime": "topSystem.attributes.currentTime",
                    "name": "topSystem.attributes.name",
                    "uptime": "topSystem.attributes.systemUpTime"
                }])
        
        data = glom(system, keep)[0]
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


    def _post_interfaceEntity(self, children):

        headers = { "Content-Type": "application/json" }
        payload = {
            "interfaceEntity": {
                "children": children
            }
        }

        endpoint = self.api_url + "mo/sys.json"
        self.logger.log(f"POST {endpoint}: {payload}")
        res = requests.post(endpoint, cookies=self.auth_cookie, headers=headers, data=json.dumps(payload), verify=False)
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
        if rmonEtherStats["totalCount"] == '0':
            return {}
        
        data = glom(rmonEtherStats, ("imdata", ["rmonEtherStats.attributes"]))
        
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
            delta = current_cRC - ref_cRC if current_cRC > ref_cRC else current_cRC

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
