import argparse
import os
from nxapi_requets import NXREST_API

def main(args):

    
    switchuser=os.getenv("SWITCH_USER_ID")
    switchpassword=os.getenv("SWITCH_PASSWORD")


    if switchuser == None or switchpassword == None:
            print("Incomplete .env")
            return

    sc = NXREST_API(switchuser, switchpassword, args.switch_ip)
    sc.print_system_info()    
    if(args.logs):
        sc.print_logs()
    sc.logout()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A program to communicate with NX-API on NX-OS")


    parser.add_argument("switch_ip")
    parser.add_argument("--logs", help="Get logs of the Switch", action="store_true")

    args = parser.parse_args()
    main()