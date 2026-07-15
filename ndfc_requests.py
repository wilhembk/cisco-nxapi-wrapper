import requests
import json
import re
from glom import glom 
from typing import Dict
import urllib3
from utils import ANSI, Logger
from result_file import ResultFile
from datetime import datetime

# The certificate is self-signed. So we disable warnings.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) 

class NDFC_API:
    def __init__(self, domain: str, username: str, password: str, logger: Logger, result: ResultFile):
        self.domain = domain
        self.username = username
        self.password = password
        self.logger = logger
        self.result = result
        self.token = self._get_jwttoken()
        


    def _get_jwttoken(self):

        headers={'content-type':'application/json'}
        payload={
                "domain": "local",
                "userName": self.username,
                "userPasswd": self.password
            }
        
        req = requests.post(self.domain+"/login", headers=headers, data=json.dumps(payload), verify=False)
        if req.status_code != 200:
            return ""
        return req.json().get("jwttoken")