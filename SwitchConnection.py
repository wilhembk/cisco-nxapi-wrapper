from nxapi_requets import NXCLI_API, NXREST_API
from utils import Logger
from ResultFile import ResultFile


class SwitchConnection:
    """Wraps both API types for seemless calls"""


    def __init__(self, user_id: str, password: str, switch_ip: str, logger: Logger, result: ResultFile):
        self.cli = NXCLI_API(user_id, password, switch_ip, logger, result)
        self.rest = NXREST_API(user_id, password, switch_ip, logger, result)

        self.hostname = self.rest.get_hostname() # Getting hostname by default so it appears in the result file

    def login(self):
        return self.rest.login()
    
    def logout(self):
        return self.rest.logout()
    
    def get_ifaces_down_since(self, days):
        return self.rest.get_ifaces_down_since(days)
    
    def down_ifaces(self, ifaces):
        return self.rest.down_ifaces(ifaces)