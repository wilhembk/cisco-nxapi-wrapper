"""
Author: Wilhem Blondel
Website: https://wilhemb.fr
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict

import requests
import json
import urllib3

if TYPE_CHECKING:
    from requests import Response
    from src.utils import Logger
    from src.result_file import ResultFile

# The certificate is self-signed. So we disable warnings.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) 

class NDFC_API:
    def __init__(self, domain: str, username: str, password: str, logger: Logger, result: ResultFile, timeout: int = 90):
        """
        Connection to NDFC API
        Throws Exception if it can't retrieve the connection token.
        """
        self.domain = domain
        self.username = username
        self.password = password
        self.logger = logger
        self.result = result
        self.ndfc_managed: Dict[str, bool] = dict() # serial : managed_by_ndfc ?
        self.timeout = timeout
        self.token = self._get_jwttoken()
        if self.token == "":
            raise Exception("NDFC can't connect")
        


    def _get_jwttoken(self) -> str:
        """
        PRIVATE
        Returns the jwttoken required to authenticate API calls to NDFC
        """

        headers={"content-type":"application/json"}
        payload={
                "domain": "local",
                "userName": self.username,
                "userPasswd": self.password
            }
        self.logger.log("Logging into NDFC using the provided credentials.")

        try:
            req = requests.post(self.domain+"/login", headers=headers, data=json.dumps(payload), verify=False, timeout=self.timeout)
        except requests.exceptions.Timeout:
            self.logger.log(f"Could not reach NDFC at {self.domain} within {self.timeout} seconds")
            return ""
        except Exception as err:
            self.logger.log(f"Could not reach NDFC at {self.domain}: {err}")
            return ""

        if req.status_code != 200:
            self.logger.log("Could not login to NDFC, are the credentials correct ?")
            return ""
        
        self.logger.log("Logged into NDFC successfully")
        return req.json().get("jwttoken")


    def _get_endpoint(self, endpoint: str) -> Response | None:
        """
        PRIVATE
        Wraps the GET request of the https://<ip_ndfc>/<endpoint> with the
        correct authorization header.
        Returns None in case of an error.
        """

        if self.token == "":
            return None

        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        self.logger.log(f"GET {self.domain+endpoint}")

        try:
            res = requests.get(self.domain+endpoint, headers=headers, verify=False, timeout=self.timeout)
        except requests.exceptions.Timeout:
            self.logger.log(f"GET {self.domain+endpoint} timed out after {self.timeout} seconds")
            return None
        except:
            self.logger.log(f"Could not fetch NDFC ressource at {self.domain+endpoint}")
            return None
        
        return res
    
    def _post_endpoint(self, endpoint: str, payload: str) -> Response | None:
        """
        PRIVATE
        Wraps the POST request of the https://<ip_ndfc>/<endpoint> with the
        correct authorization header.
        Returns None in case of an error.
        """

        if self.token == "":
            return None


        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        self.logger.log(f"POST {self.domain+endpoint}")

        try:
            res = requests.post(self.domain+endpoint, data=payload, headers=headers, verify=False, timeout=self.timeout)
        except requests.exceptions.Timeout:
            self.logger.log(f"POST {self.domain+endpoint} timed out after {self.timeout} seconds")
            return None
        except:
            self.logger.log(f"Could not POST payload to NDFC {self.domain+endpoint}")
            return None
        
        return res
    

    def is_managed_by_ndfc(self, serial_number: str) -> bool | None:
        """
        Check if NDFC manages this serial number by getting intent-interfaces
        if intent-interfaces is empty, we say that ndfc does not
        manage this switch.
        Returns None if management by NDFC is unsure because of 
        an internal server error, or a failed connection.
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
        """
        Shuts the requested ports on NDFC and push the result in the ResultFile
        Returns if the shutdown was successfull or not
        """

        if len(ports) == 0:
            return True


        if not self.is_managed_by_ndfc(serial_number):
            return False
        

        formatted_ports = [iface.replace("eth", "Ethernet") for iface in ports]

        payload: Dict[str, str | List[Dict[str, str]]] = {
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