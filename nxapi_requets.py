import requests
import json
from glom import glom 

class SwitchConnection:

    def __init__(self, user_id: str, password: str, switch_ip: str):
        self.user_id = user_id
        self.password = password
        self.endpoint = f"http://{switch_ip}/ins"

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
            auth=(self.user_id,self.password)
        ).json()

        return response
    

    def get_hostname(self):
        return glom(self._wrap_cmd("show switchname"), "result.body.hostname")
    

class NXREST_API:

    def __init__(self, user_id: str, password: str, switch_ip: str):
        self.user_id = user_id
        self.password = password
        self.switch_ip = switch_ip
        self.api_url = f"http://{self.switch_ip}/api/"

        self.auth_cookie = {}
        self._login()


    def _login(self):
        payload = {
        'aaaUser' : {
            'attributes' : {
                'name' : self.user_id,
                'pwd' : self.password,
                }
            }
        }

        endpoint = self.api_url+"aaaLogin.json"

        response = requests.request("POST", endpoint, data=json.dumps(payload))
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
        requests.request("POST", endpoint, data=json.dumps(payload), cookies=self.auth_cookie)
        self.auth_cookie = {}


    def _get(self, json_file: str):
        endpoint = f"{self.api_url}/mo/{json_file}"
        return requests.request("GET", endpoint, cookies=self.auth_cookie).json()
    
    def get_hostname(self):
        res = self._get("sys.json")
        return glom(res, ("imdata", ["topSystem.attributes.name"]))[0]
