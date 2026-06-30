import requests
import json
from glom import glom 
import urllib3
from utils import ANSI

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

    def __init__(self, user_id: str, password: str, switch_ip: str):
        self.user_id = user_id
        self.password = password
        self.switch_ip = switch_ip
        self.api_url = f"https://{self.switch_ip}/api/"

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

        response = requests.request("POST", endpoint, data=json.dumps(payload), verify=False)
        if response.status_code == requests.codes.ok:
            data = json.loads(response.text)['imdata'][0]
            token = str(data['aaaLogin']['attributes']['token'])
            self.auth_cookie = {"APIC-cookie" : token}
            
        else:
            raise Exception("Could not login to NX-API REST. Is the feature enabled ? Are the credentials correct ?")
        
    
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
        response = requests.request("GET", endpoint, cookies=self.auth_cookie, verify=False)
        if response.status_code != requests.codes.ok:
            print(f"ERROR: No target for {endpoint}")
            return {}
        return response.json()
    
    def _get_system(self):
        return self._get("mo/sys.json")

    def get_hostname(self):
        return glom(self._get_system(), ("imdata", ["topSystem.attributes.name"]))[0]


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

    def _get_faults(self):
        return self._get("class/faultInst.json")


    def print_logs(self):

        faults = self._get_faults()

        if faults["totalCount"] == '0':
            return 

        keep = ("imdata", 
                [{
                    "cause":"faultInst.attributes.cause",
                    "code":"faultInst.attributes.code",
                    "descr":"faultInst.attributes.descr",
                    "dn":"faultInst.attributes.dn",
                    "severity":"faultInst.attributes.severity"
                }]
                )
        
        data = glom(faults, keep)

        
        for log in data:
            prefix = ""
            if log["severity"].upper() == "WARNING":
                prefix = f"{ANSI.COLOR_YELLOW} "
            else:
                prefix = f"{ANSI.COLOR_RED} "
            print(f"{prefix}[{log["severity"].upper()}] ({log["code"]}) at \"{log["dn"]}\" : {log["descr"]}. Caused by {log["cause"]} {ANSI.RESET_ALL}")