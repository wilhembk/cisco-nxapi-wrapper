import argparse
import os, sys
from nxapi_requets import NXREST_API
from utils import Logger, ResultFile

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
    result = ResultFile(args.result_dir_path)

    for ip in f.readlines(): 
        ip = ip.strip()
        sw = NXREST_API(switchuser, switchpassword, ip, logger, result)  
        if(args.unused_ports != None):
            sw.get_ifaces_down_since(args.unused_ports)
        sw.print_system_info()
        sw.print_ifaces(filter_admin_down=True)
        sw.logout()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A program to maintain Cisco switched through NX-API calls")

    parser.add_argument("switch_ip_list", help="The file containing all the switch ips (separated by a newline)")
    parser.add_argument("log_dir_path", help="The directory on where to store logs of the program")
    parser.add_argument("result_dir_path", help="The directory on where to store results of the program")
    parser.add_argument("--unused_ports", type=int, help="Check for DOWN ports unused since N days")

    args = parser.parse_args()
    main(args)