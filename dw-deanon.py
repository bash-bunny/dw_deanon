#!/usr/bin/env python3

import os, re, hashlib, requests, argparse, codecs, json
import shodan
from pathlib import Path
from censys.search import CensysHosts
import zoomeyeai.sdk as zoomeye
from dotenv import load_dotenv, dotenv_values
from urllib3.exceptions import InsecureRequestWarning
from bs4 import BeautifulSoup

# Load the API KEYS
load_dotenv()
zoomeye_api = os.getenv("ZOOMEYE_KEY")
shodan_api = os.getenv("SHODAN_KEY")
censys_api_file = Path("~/.config/censys/censys.cfg").expanduser()

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

# Get the title for a domain
def fetch_title(domain, timeout=60):
    title = ""
    try:
        r = session.get(domain, timeout=timeout)
        soup = BeautifulSoup(r.content, 'html.parser')
        title = soup.title.string
    except Exception as e:
        print(f"Exception retrieving the title: {e}")
    return title

# Retrieve favicon from the webpage
def fetch_favicon(url, path, timeout=60):
    succeed = False
    try:
        r = session.get(url, timeout=timeout)
        if r.status_code == 200:
            with open(path+"/favicon.ico", "wb") as f:
                f.write(r.content)
                succeed = True
        else:
            print(f"[!] The {url} does not have a favicon")
        return succeed
    except Exception as e:
        print(f"[!] Exception retrieving the favicon: {e}")
        return succeed

# Calculate the md5 hash for the favicon.ico file
def generate_favicon_hash(favicon_file):
    with open(favicon_file, "rb") as file:
        favicon_data = file.read()
        encoded_data = codecs.encode(favicon_data, "base64")
        return hashlib.md5(favicon_data).hexdigest()

# Check the server-status path
def check_server_status(url, path, timeout=60):
    succeed = False
    try:
        r = session.get(url, timeout=timeout)
        if r.status_code == 200:
            succeed = True
            write_results(r.text, path)
    except Exception as e:
        print(f"[!] Exception accessing the /server-status path: {e}")
    return succeed

# Write results
def write_results(results, out_file):
    with open(out_file, "a", encoding="utf-8") as f:
        f.write(results)

# Zoomeye search
def zoomeye_search(api_key, search, path):
    try:
        zm = zoomeye.ZoomEye(api_key=api_key)
        data = zm.search(search)
        if data:
            write_results(data, path)
    except Exception as e:
        print(f"[!] Exception searching with zoomeye: {e}")

# Shodan search
def shodan_search(api_key, search, path):
    try:
        api = shodan.Shodan(api_key)
        data = api.search(search)
        if data['total'] > 0:
            print(data['matches'])
            write_results(json.dumps(data), path)
    except Exception as e:
        print(f"[!] Exception searching with shodan: {e}")

# Censys search
def censys_search(search, path):
    h = CensysHosts()
    try:
        query = h.search(search)
        data = query.view_all()
        if len(data) > 0:
            print(data)
            write_results(json.dumps(data), path)
    except Exception as e:
        print(f"[!] Exception searching with censys: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dark Web Deanonimization")
    parser.add_argument("--domain", help="Dark web domain to try to deanonimize")
    args = parser.parse_args()

    if args.domain:
        # Check if it's an onion domain
        if not re.search(r'.*onion$', args.domain):
            # If not exit
            print("[!] That's not a dark web domain")
            exit()
        else:
            # Test connectivity through TOR
            if not test_tor_connection():
                print("[!] Tor connection failed. Please start Tor (e.g., `tor` or `service tor start`).")
                exit()
            # If it's connected to the TOR network grab the domain
            domain = re.sub(r"https?://", "", args.domain)

        # Create folder to store the results for a particular domain
        folder = domain.replace(".","_")
        create_folder(folder)
        path = os.path.join(folder, "results.txt")

        # Variables to check deanon
        url = ""
        tls = ""
        title = ""
        favicon_hash = ""

        # Results for domain
        write_results(f"Results for {domain}\n", path)

        # Check TLS
        tls = check_tls(domain)
        if (tls != 0):
            url = "https://"+domain
            print(f"TLS hash for {domain}")
            print(f"{tls}")
            write_results(f"TLS hash: {tls}\n", path)
        else:
            url = "http://"+domain
            print(f"[!] The {domain} do not use TLS")

        # Fetch title
        title = fetch_title(url)
        if title:
            print(f"Title for {domain}")
            print(f"{title}")
            write_results(f"Title: {title}\n", path)

        # Fetch favicon
        url_favicon = url+"/favicon.ico"
        if fetch_favicon(url_favicon, folder):
            favicon_file = os.path.join(folder, "favicon.ico")
            favicon_hash = generate_favicon_hash(favicon_file)
            print(f"Favicon hash for {domain}")
            print(f"{favicon_hash}")
            write_results(f"Favicon hash: {favicon_hash}\n", path)

        # Check server-status
        url_server_status = url+"/server-status"
        server_status_results = os.path.join(folder, "server_status.html")
        server_status = check_server_status(url_server_status, server_status_results)
        if server_status:
            print(f"Server Status available on {domain}")
            write_results(f"Server status available on: {url}/server-status\n", path)

        if zoomeye_api:
            zoomeye_results = os.path.join(folder, "zoomeye_results.json")
            print(f"Searching with Zoomeye...")
            zoomeye_search(zoomeye_api, domain, zoomeye_results)
            if tls:
                search = f"ssl.cert.fingerprint={tls}"
                zoomeye_search(zoomeye_api, search, zoomeye_results)
            if title:
                search = f"title='{title}'"
                zoomeye_search(zoomeye_api, search, zoomeye_results)
            if favicon_hash:
                search = f"iconhash='{favicon_hash}'"
                zoomeye_search(zoomeye_api, search, zoomeye_results)
        if censys_api_file.is_file() and censys_api_file.stat().st_size > 0:
            censys_results = os.path.join(folder, "censys_results.json")
            print(f"Searching with Censys...")
            censys_search(domain, censys_results)
            if tls:
                search = f"fingerprint_sha1:'{tls}'"
                censys_search(search, censys_results)
            if title:
                search = f"services.http.response.html_title: '{title}'"
                censys_search(search, censys_results)
            if favicon_hash:
                search = f"services.http.response.favicons.hashes:'{favicon_hash}'"
                censys_search(search, censys_results)
        if shodan_api:
            shodan_results = os.path.join(folder, "shodan_results.json")
            print(f"Searching with Shodan...")
            shodan_search(shodan_api, domain, shodan_results)
            if tls:
                search = f"ssl.cert.fingerprint:{tls}"
                shodan_search(shodan_api, search, shodan_results)
            if title:
                search = f"title:'{title}'"
                shodan_search(shodan_api, search, shodan_results)
            if favicon_hash:
                search = f"http.favicon.hash:'{favicon_hash}'"
                shodan_search(shodan_api, search, shodan_results)

        print(f"Finished, check results inside {folder}")
    else:
        parser.print_help()
