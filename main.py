import argparse
import os, sys
from switch_connection import SwitchConnection
from utils import Logger
from result_file import ResultFile
from typing import List

from dotenv import load_dotenv

load_dotenv() # Loading the .env file containing password and username for the switches


# When you add a new monitoring feature:

# 1. Add a facade method on `SwitchConnection` delegating to nxapi_requests.

# 2. Add `parser.add_argument` in the `if __name__ == "__main__"` block below.

# 3. Check for your flag with args.<your_flag_name>

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
        sw = SwitchConnection(switchuser, switchpassword, ip, logger, result, args.demo_path)  
        success = sw.login()
        if not success:
            continue
        if args.unused_ports != None:
            ifaces = sw.get_ifaces_down_since(args.unused_ports)
            sw.down_ifaces(ifaces)
        
        if args.half_duplex:
            sw.get_half_duplex()

        if args.check_transceivers != None:
            sw.check_for_tranceiver_alerts(filter_warn=(args.check_transceivers == "ALERT"))

        if args.CRC != None:
            critical_delta = args.CRC[0]
            reference_directory_path = args.CRC[1]
            sw.get_cRCAlignErrors(critical_delta, reference_directory_path)

        sw.logout()
        
    result.commit()




    

if __name__ == "__main__":

    counter = 0
    def critical_delta(input):
        global counter
        if counter == 0:
            counter = 1
            return int(input)
        else:
            counter = 0
            return input
            

    parser = argparse.ArgumentParser(description="A program to maintain Cisco switched through NX-API calls")
    # Add CLI flags here for new checks. Use descriptive names and document their behaviour on the documentation
    
    parser.add_argument("switch_ip_list", help="The file containing all the switch ips (separated by a newline)")
    parser.add_argument("log_dir_path", help="The directory on where to store logs of the program")
    parser.add_argument("result_dir_path", help="The directory on where to store results of the program")
    parser.add_argument("--unused_ports", type=int, metavar="N", help="Check for DOWN ports unused since N days")
    parser.add_argument("--half_duplex", action="store_true", help="Check for interfaces running in half duplex mode")
    parser.add_argument("--check_transceivers", choices=["WARN", "ALERT"], help="Check transceivers hardware and notify for issues higher or equal to specified level")
    parser.add_argument("--CRC", nargs=2, type=critical_delta, metavar=("critical_delta","reference_directory_path"), help="Check for additional cRC and Align errors according to the reference directory")
    parser.add_argument("--demo_path", metavar="demo_directory_path", help="Enable demo and read local files instead of switch API. For testing purposes only.")

    args = parser.parse_args()
    main(args)



