
import os
from dotenv import load_dotenv
from nxapi_requets import SwitchConnection

load_dotenv()


"""
client_cert_auth=False
client_cert='PATH_TO_CLIENT_CERT_FILE'
client_private_key='PATH_TO_CLIENT_PRIVATE_KEY_FILE'
ca_cert='PATH_TO_CA_CERT_THAT_SIGNED_NXAPI_SERVER_CERT'
"""


def main():

    switchuser=os.getenv("SWITCH_USER_ID")
    switchpassword=os.getenv("SWITCH_PASSWORD")

    if switchuser == None or switchpassword == None:
        print("Incomplete .env")
        return

    sc = SwitchConnection(switchuser, switchpassword, "192.168.1.1")
    res = sc.get_hostname()
    print(res)

main()