import argparse
import os
from src.switch_connection import SwitchConnection
from src.ndfc_requests import NDFC_API
from src.utils import Logger, down_ifaces
from src.result_file import ResultFile

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

    ndfc_url = os.getenv("NDFC_URL")
    ndfc_user = os.getenv("NDFC_USER")
    ndfc_password = os.getenv("NDFC_PASSWORD")

    ndfc_conn = None

    if (ndfc_url != None or ndfc_user != None or ndfc_password != None) and args.unused_ports != None and args.unused_ports[1] in (2,3):
        if ndfc_url == None or ndfc_user == None or ndfc_password == None:
            print("Please pass all NDFC_URL, NDFC_USER and NDFC_PASSWORD in .env file (or don't pass any.)")
            return
        
        try:
            ndfc_conn = NDFC_API(ndfc_url, ndfc_user, ndfc_password, logger, result, args.timeout)
        except:
            ndfc_conn = None
        
    for ip in f.readlines(): 
        ip = ip.strip()
        sw = SwitchConnection(switchuser, switchpassword, ip, logger, result, args.demo_path, args.timeout)  
        success = sw.login()
        if not success:
            continue

        if args.unused_ports != None:
            ifaces = sw.get_ifaces_down_since(args.unused_ports[0])
            auto_down = args.unused_ports[1]
            down_ifaces(ifaces, auto_down, sw, ndfc_conn, logger)
        
        if args.half_duplex:
            sw.get_half_duplex()

        if args.err_disabled:
            sw.get_ifaces_err_disabled()

        if args.check_transceivers != None:
            sw.check_for_tranceiver_alerts(filter_warn=(args.check_transceivers == "ALERT"))

        if args.CRC != None:
            critical_delta = args.CRC[0]
            reference_directory_path = args.CRC[1]
            sw.get_cRCAlignErrors(critical_delta, reference_directory_path)

        if args.PTP != None:
            since = args.PTP[0]
            log_level = args.PTP[1]
            critical_correction = args.PTP[2]
            sw.check_ptp(since, log_level, critical_correction)


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
            

    parser = argparse.ArgumentParser(description="A program to maintain Cisco switches through NX-API calls")
    # Add CLI flags here for new checks. Use descriptive names and document their behaviour on the documentation
    
    parser.add_argument("switch_ip_list", help="The file containing all the switch ips (separated by a newline)")
    parser.add_argument("log_dir_path", help="The directory on where to store logs of the program")
    parser.add_argument("result_dir_path", help="The directory on where to store results of the program")
    parser.add_argument("-u", "--unused_ports", nargs=2, type=int, metavar=("N", "auto_down"), help="Check for DOWN ports unused since N days. Use auto_down=0 to not automaticlly set the associated interfaces as admin_down, auto_down=1 to down the interfaces DIRECTLY on the switch, auto_down=2 to down the interfaces via NDFC only, and auto_down=3 to try to down the interfaces via NDFC and fallback to a down the interfaces DIRECTLY on the switch")
    parser.add_argument("-d","--half_duplex", action="store_true", help="Check for interfaces running in half duplex mode")
    parser.add_argument("-e","--err_disabled", action="store_true", help="Check for interfaces that are disabled due to an error")
    parser.add_argument("-t","--check_transceivers", choices=["WARN", "ALERT"], help="Check transceivers hardware and notify for issues higher or equal to specified level")
    parser.add_argument("-c","--CRC", nargs=2, type=critical_delta, metavar=("critical_delta","reference_directory_path"), help="Check for additional cRC and Align errors according to the reference directory")
    parser.add_argument("-p", "--PTP", nargs=3, type=int, metavar=("since","log_level", "critical_correction"), help="Check for abnormal PTP activity. Use log_level=0 to never output PTP logs, log_level=1 to output only on abnormal activity and log_level=2 to always output")
    parser.add_argument("--timeout", type=int, default=90, help="Timeout in seconds for each NX-API and NDFC request")
    parser.add_argument("--demo_path", metavar="demo_directory_path", help="Enable demo and read local files instead of switch API. For testing purposes only.")

    args = parser.parse_args()
    main(args)



