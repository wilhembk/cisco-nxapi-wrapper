import requests
import json
from response_wrapper import ResponseWrapper

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

        return ResponseWrapper(response)
    

    def get_hostname(self):
        return self._wrap_cmd("show switchname").get("result.body.hostname")