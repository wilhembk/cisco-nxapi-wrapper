import requests
import json
from glom import glom 
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
        return list(filter(
                lambda iface: iface["sfp"] == "present", 
                glom(self._wrap_cmd("show interface transceiver details"), "result.body.TABLE_interface.ROW_interface")))
    
    def check_for_tranceiver_alerts(self):
        # Check for duplex
        transceivers = self.get_transceiver_details()


        #self.result.output("--- Transceivers alerts ---")
        for tran in transceivers:
            iface = tran["interface"]
            if "TABLE_lane" not in tran.keys:
                # No data
                continue

            lanes = tran["TABLE_lane"]
            for lane in lanes:
                if "tx_alrm_hi" in lane.keys:
                    # This an optic cable
                    self.check_light_level_lane(iface, lane)
        #self.result.output("--------------------------")

    def check_light_level_lane(self, iface, lane):

        if "tx_pwr" not in lane.keys:
            self.logger.log(f"No cable connected for lane {lane["lane_number"]} in {iface} !")
            #self.result.output(f"!!! Lane {lane["lane_number"]} on {iface} has NO CABLE !!!")

        tx_alrm_hi = lane["tx_pwr_alrm_hi"]
        tx_alrm_low = lane["tx_pwr_alrm_lo"]
        tx_warn_hi = lane["tx_pwr_warn_hi"]
        tx_warn_low = lane["tx_pwr_warn_lo"]
        tx = lane["tx_pwr"]




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
        data = self.get_ifaces_states(filter_admin_down=True, filter_absent=True)
        
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
        
        self.result.set_unused_ports(hostname=self.get_hostname(), port_list=unused_ports, unused_since=days)
        return unused_ports  


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
        self.result.set_unused_ports(hostname=self.get_hostname(), successful_down=success)
        if success:
            self.logger.log(f"Successfully disabled {[iface["readable_id"] for iface in ifaces]}")

        




    def _get_stp(self):
        return self._get("class/stpIf.json")
