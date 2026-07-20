import requests
from requests import Response
import json
import urllib3
from src.utils import Logger
from src.result_file import ResultFile
from typing import List

# The certificate is self-signed. So we disable warnings.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) 

class NDFC_API:
    def __init__(self, domain: str, username: str, password: str, logger: Logger, result: ResultFile):
        self.domain = domain
        self.username = username
        self.password = password
        self.logger = logger
        self.result = result
        self.ndfc_managed = dict()
        self.token = self._get_jwttoken()
        


    def _get_jwttoken(self):

        headers={"content-type":"application/json"}
        payload={
                "domain": "local",
                "userName": self.username,
                "userPasswd": self.password
            }
        self.logger.log("Logging into NDFC using the provided credentials.")

        try:
            req = requests.post(self.domain+"/login", headers=headers, data=json.dumps(payload), verify=False)
        except:
            self.logger.log(f"Could not reach NDFC at {self.domain}")
            return ""

        if req.status_code != 200:
            self.logger.log("Could not login to NDFC, are the credentials correct ?")
            return ""
        
        self.logger.log("Logged into NDFC successfully")
        return req.json().get("jwttoken")


    def _get_endpoint(self, endpoint: str) -> Response | None:

        if self.token == "":
            return None

        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        self.logger.log(f"GET {self.domain+endpoint}")

        try:
            res = requests.get(self.domain+endpoint, headers=headers, verify=False)
        except:
            self.logger.log(f"Could not fetch NDFC ressource at {self.domain+endpoint}")
            return None
        
        return res
    
    def _post_endpoint(self, endpoint: str, payload: str) -> Response | None:

        if self.token == "":
            return None


        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        self.logger.log(f"POST {self.domain+endpoint}")

        try:
            res = requests.post(self.domain+endpoint, data=payload, headers=headers, verify=False)
        except:
            self.logger.log(f"Could not POST payload to NDFC {self.domain+endpoint}")
            return None
        
        return res
    

    def is_managed_by_ndfc(self, serial_number: str) -> bool | None:
        """
        Check if NDFC manages this serial number by getting intent-interfaces
        if intent-interfaces is empty, we say that ndfc does not
        manage this switch.
        """

        if self.token == "":
            return None


        if serial_number in self.ndfc_managed.keys():
            return self.ndfc_managed[serial_number]

        self.logger.log(f"Checking if {serial_number} is managed by NDFC")
        endpoint = f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/policies/switches/{serial_number}/intent-interfaces"

        req = self._get_endpoint(endpoint)

        if req == None or req.status_code != 200:
            return None
        
        if len(req.json()) == 0:
            self.logger.log(f"{serial_number} is not managed by NDFC. Will not retry to communicate with this switch via NDFC.")
            self.ndfc_managed[serial_number] = False
            return False
        
        self.ndfc_managed[serial_number] = True
        return True
            
    

    def shut_ports(self, switch_ip: str, serial_number: str, ports: List[str]) -> bool:
        """Returns if the shutdown was successfull or not"""

        if len(ports) == 0:
            return True


        if not self.is_managed_by_ndfc(serial_number):
            return False
        

        formatted_ports = [iface.replace("eth", "Ethernet") for iface in ports]

        payload = {
            "operation": "shut",
            "interfaces": [
                {
                "serialNumber": serial_number,
                "ifName": iface
                }
            for iface in formatted_ports]
        }

        endpoint = "/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/interface/adminstatus"
        req = self._post_endpoint(endpoint, json.dumps(payload))

        if req == None or req.status_code != 200:
            return False

        self.result.set_unused_ports(ip_addr=switch_ip, successful_down=True)
        self.logger.log(f"Successfully disabled {[iface for iface in ports]} via NDFC.")
        return True