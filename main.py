import argparse
import os, sys
from nxapi_requets import NXREST_API
from utils import Logger

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
        print(f"Could not open {args.switch_ip_list}")
        return
    
    logger = Logger(args.log_dir_path)

    for ip in f.readlines(): 
        ip = ip.strip()
        sw = NXREST_API(switchuser, switchpassword, ip, logger)  
        if(args.unused_ports != None):
            sw.get_ifaces_down_since(args.unused_ports)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A program to communicate with NX-API on NX-OS")

    parser.add_argument("switch_ip_list", help="The file containing all the switch ips (separated by a newline)")
    parser.add_argument("log_dir_path", help="The directory on where to store logs of the programs")
    parser.add_argument("--unused_ports", type=int, help="Check for DOWN ports unused since N days")

    args = parser.parse_args()
    main(args)