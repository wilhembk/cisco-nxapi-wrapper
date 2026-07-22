from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, List

from src.nxapi_requests import NXCLI_API, NXREST_API

if TYPE_CHECKING:
    from src.utils import Logger
    from src.result_file import ResultFile

# NOTE: `SwitchConnection` is the public facade used by `main.py`.
# When you add a new monitoring method to `NXREST_API` or `NXCLI_API`, add a
# corresponding method here that delegates to `self.rest` or `self.cli`.

class SwitchConnection:
    """Wraps both API types for seemless calls"""


    def __init__(self, user_id: str, password: str, switch_ip: str, logger: Logger, result: ResultFile, demo_path: str | None = None, timeout: int = 90):
        self.cli = NXCLI_API(user_id, password, switch_ip, logger, result, demo_path, timeout)
        self.rest = NXREST_API(user_id, password, switch_ip, logger, result, demo_path, timeout)
        self.switch_ip = switch_ip
        self.hostname, self.serial = None, None

    def login(self):
        """
        Login into NXAPI-REST, fetching hostname and serial number if the connection succeeded.
        Returns False in case of connection failure
        Call logout to shut down the connection gracefully
        """
        res = self.rest.login()
        if res:
            # Getting hostname by default so it appears in the result file
            self.hostname, self.serial = self.rest.get_hostname_and_serial()
        return res
            
    
    def logout(self):
        """
        Closes the NXAPI-REST connection gracefully
        """
        return self.rest.logout()
    
    def get_ifaces_down_since(self, days: int) -> List[Dict[str, Any]]:
        """
        Returns a list of unused ports state given the time period
        Do not check for admin_down interfaces.
        Reports data in the ResultFile
        """
        return self.rest.get_ifaces_down_since(days)
    
    def down_ifaces(self, ifaces: List[Dict[str, Any]]) -> None:
        """Admin down interfaces with REST API. BEWARE of NDFC compatibility issues."""
        return self.rest.down_ifaces(ifaces)
    
    def get_half_duplex(self) -> List[Dict[str, Any]]:
        """
        Returns a list of ports state running in half_duplex
        Do not check for admin_down or unplugged interfaces.
        Reports data in the ResultFile
        """
        return self.rest.get_half_duplex()
    
    def get_cRCAlignErrors(self, critical_delta: int, ref_file_path: str) -> None:
        """
        Checks for cRC counters exceeding the provided threshold according to the reference data.
        Reports issues in the ResultFile
        """
        return self.rest.get_cRCAlignErrors(critical_delta, ref_file_path)
    
    def check_for_tranceiver_alerts(self, filter_warn: bool = False) -> None:
        """
        Checks transceivers status and alerts in the ResultFile in case of issues
        if filter_warn is set to True, warnings are not issued
        """
        return self.cli.check_for_tranceiver_alerts(filter_warn)
    
    def check_ptp(self, since: int, log_level: int, critical_correction: int):
        """
        Checks for PTP unusual behaviour (GM changes, and correction)
        Reports in the ResultFile
        """
        return self.cli.check_ptp(since, log_level, critical_correction)

    def get_ifaces_err_disabled(self):
        """
        Returns a list of ports state that were shut because of an error
        Do not check for admin_down or unplugged interfaces.
        Reports data in the ResultFile
        """
        return self.rest.get_ifaces_err_disabled()