import argparse
import os, sys
from nxapi_requets import NXREST_API

from dotenv import load_dotenv

load_dotenv()

def main(args):

    
    switchuser=os.getenv("SWITCH_USER_ID")
    switchpassword=os.getenv("SWITCH_PASSWORD")


    if switchuser == None or switchpassword == None:
            print("Please pass SWITCH_USER_ID and SWITCH_PASSWORD in a .env file")
            return
    
    try:
        f = open(args.switch_ip_list, "r")
    except:
        print(f"Could not open {args.swicth_ip_list}")
        return

    for ip in f.readlines(): 
        print("------------------------")
        sw = NXREST_API(switchuser, switchpassword, ip)
        sw.print_system_info()    
        if(args.logs):
            sw.print_logs()
        if(args.ifstate):
            sw.print_ifaces()
        sw.logout()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A program to communicate with NX-API on NX-OS")

    parser.add_argument("switch_ip_list", help="The file containing all the switch ips (separated by a newline)")
    parser.add_argument("--logs", help="Get logs of the Switch", action="store_true")
    parser.add_argument("--ifstate", help="Get interface states", action="store_true")

    args = parser.parse_args()
    main(args)