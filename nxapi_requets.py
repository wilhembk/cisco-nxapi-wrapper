import requests
import json
from glom import glom 
import urllib3
from utils import ANSI, Logger, ResultFile
import sys
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SwitchConnection:

    def __init__(self, user_id: str, password: str, switch_ip: str):
        self.user_id = user_id
        self.password = password
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
    

class NXREST_API:

    def __init__(self, user_id: str, password: str, switch_ip: str, logger: Logger, result: ResultFile):
        self.user_id = user_id
        self.password = password
        self.switch_ip = switch_ip
        self.api_url = f"https://{self.switch_ip}/api/"
        self.logger = logger
        self.result = result
        self.auth_cookie = {}
        self.login()


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
            self.result.begin_switch_result(self.get_hostname())
              
        else:
            self.logger.log(f"Login into {self.switch_ip} failed. Are the credentials correct ? Aborting.")
            sys.exit(1)
        
    
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
        self.result.end_switch_result()


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
        self.logger.log(f"Getting switch hostname")
        return glom(self._get_system(), ("imdata", ["topSystem.attributes.name"]))[0]


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
            data[i]["dn"] = data[i]["dn"].lstrip("sys/intf/phys-[").rstrip("]/phys") 
            # Show as "eth1/33" where 1 is the card number, and 33 the port number.

        return data


    def print_ifaces(self, filter_admin_down=False, filter_absent=False):
        """
        Print current interfaces state. Can filter out absent interfaces and interface
        down by an admin.
        """

        data = self.get_ifaces_states(filter_admin_down, filter_absent)

        for iface in data:

            s = iface["dn"]

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
            self.logger.log(f"{iface["dn"]} is down since {down_days} days. Disable or unplug.")
            unused_ports.append(iface["dn"])
        
        self.result.unused_ports(days, unused_ports)            

    def _get_stp(self):
        return self._get("class/stpIf.json")
