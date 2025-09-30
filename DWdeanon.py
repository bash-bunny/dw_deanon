#!/usr/bin/env python3

import os
import re
import requests
import argparse
import zoomeyeai.sdk as zoomeye
from dotenv import load_dotenv, dotenv_values

# Set Global Session through TOR
session = requests.session()
session.proxies = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}

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

def create_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dark Web Deanonimization")
    parser.add_argument("--domain", help="Dark web domain to try to deanonimize")
    args = parser.parse_args()

    # Test connectivity through TOR
    if not test_tor_connection():
        print("[!] Tor connection failed. Please start Tor (e.g., `tor` or `service tor start`).")
        exit
    else:
        if args.domain:
            # Check if it's an onion domain
            if not re.search(r'.*onion$', args.domain):
                # If not exit
                print("[!] That's not a dark web domain")
                exit
            else:
                # If yes get the domain
                domain = re.sub(r"https?://", "", args.domain)

            # Create folder to store the results for a particular domain
            folder = domain.replace(".","_")
            create_folder(folder)

            # Load the API KEYS
            load_dotenv()
            zoomeye_api = os.getenv("ZOOMEYE_KEY")
            censys_api = os.getenv("CENSYS_KEY")
            shodan_api = os.getenv("SHODAN_KEY")
        else:
            parser.print_help()
