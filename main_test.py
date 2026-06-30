
import os
from dotenv import load_dotenv
from nxapi_requets import SwitchConnection, NXREST_API

load_dotenv()


def main():

    switchuser=os.getenv("SWITCH_USER_ID")
    switchpassword=os.getenv("SWITCH_PASSWORD")

    if switchuser == None or switchpassword == None:
        print("Incomplete .env")
        return

    sc = NXREST_API(switchuser, switchpassword, "192.168.1.1")
    sc.print_system_info()    
    sc.print_logs()
    sc.logout()

main()