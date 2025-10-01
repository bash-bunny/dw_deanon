#!/usr/bin/env python3

import os
import re
import hashlib
import requests
import argparse
import zoomeyeai.sdk as zoomeye
from dotenv import load_dotenv, dotenv_values
from urllib3.exceptions import InsecureRequestWarning


# Set Global Variables
## Suppress the warnings from urllib3
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
## Session through TOR
session = requests.session()
session.proxies = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}
## Not verify the certificates
session.verify = False
## Results file
results = "results.txt"

# Check TOR connection
def test_tor_connection(timeout=15):
    try:
        r = session.get('http://check.torproject.org', timeout=timeout)
        if "Congratulations" in r.text:
            #print("[+] Connected through Tor successfully!")
            return True
        else:
            print("[!] Connected, but Tor test page did not confirm.")
            return False
    except Exception as e:
        print(f"[!] Tor connection failed: {e}")
        return False

# Create a folder to store results using the domain name
def create_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

# Connect using the https protocol and extract the certificate hash if
# the connection was succesful
def check_tls(domain, timeout=60):
    try:
        with session.get("https://"+domain, stream=True, timeout=timeout) as r:
            der_cert = r.raw.connection.sock.getpeercert(binary_form=True)
            sha256_fingerprint = hashlib.sha256(der_cert).hexdigest()
            return sha256_fingerprint
    except Exception as e:
        return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dark Web Deanonimization")
    parser.add_argument("--domain", help="Dark web domain to try to deanonimize")
    args = parser.parse_args()

    if args.domain:
        # Check if it's an onion domain
        if not re.search(r'.*onion$', args.domain):
            # If not exit
            print("[!] That's not a dark web domain")
            exit
        else:
            # Test connectivity through TOR
            if not test_tor_connection():
                print("[!] Tor connection failed. Please start Tor (e.g., `tor` or `service tor start`).")
                exit
            # If it's connected to the TOR network grab the domain
            domain = re.sub(r"https?://", "", args.domain)

        # Create folder to store the results for a particular domain
        folder = domain.replace(".","_")
        create_folder(folder)

        # Check TLS
        tls = check_tls(domain)
        if (tls != 0):
            print(f"The {domain} use TLS")
            print(tls)
        else:
            print(f"[!] The {domain} do not use TLS")

        # Load the API KEYS
        #load_dotenv()
        #zoomeye_api = os.getenv("ZOOMEYE_KEY")
        #censys_api = os.getenv("CENSYS_KEY")
        #shodan_api = os.getenv("SHODAN_KEY")
    else:
        parser.print_help()
