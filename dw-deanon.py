#!/usr/bin/env python3

import os, re, hashlib, requests, argparse, codecs, json, time
import shodan
from pathlib import Path
import zoomeyeai.sdk as zoomeye
from dotenv import load_dotenv, dotenv_values
from urllib3.exceptions import InsecureRequestWarning
from bs4 import BeautifulSoup

# Set Global Variables
## Suppress the warnings from urllib3
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
## Session for making requests
session = requests.Session()
session.proxies = {
    'http': 'socks5h://127.0.0.1:9153',
    'https': 'socks5h://127.0.0.1:9153'
}
# Custom user-agent
session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0'})
# Not verify the certificates
session.verify = False

# requests variables
proxies = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}
headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0'}
verify = False

# Load the API KEYS
load_dotenv()
zoomeye_api = os.getenv("ZOOMEYE_KEY")
shodan_api = os.getenv("SHODAN_KEY")
censys_orgid = os.getenv("CENSYS_ORG_ID")
censys_token = os.getenv("CENSYS_TOKEN")
modat_api = os.getenv("MODAT_KEY")

# Censys Config
censys_headers = ""
if censys_orgid and censys_token:
    censys_headers = {'X-Organization-ID': censys_orgid,
                      'Accept': 'application/vnd.censys.api.v3.host.v1+json',
                      'Authorization': 'Bearer '+censys_token}
censys_search_url = "https://api.platform.censys.io/v3/global/search/query"

# Modat Config
modat_headers = ""
if modat_api:
    modat_headers = {'Authorization': modat_api }
modat_search_url = "https://api.magnify.modat.io/service/search/v1"


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
        r = requests.get(domain, timeout=timeout, headers=headers, proxies=proxies, verify=verify)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            if soup.title:
                return soup.title.string
        print("[!] Couldn't retrieve the title")
    except Exception as e:
        print(f"[!] Exception retrieving the title: {e}")

# Retrieve favicon from the webpage
def fetch_favicon(url, path, timeout=60):
    succeed = False
    try:
        r = requests.get(url, timeout=timeout, headers=headers, proxies=proxies, verify=verify)
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
        r = requests.get(url, timeout=timeout, headers=headers, proxies=proxies, verify=verify)
        if r.status_code == 200 and "server version" in r.text.lower():
            succeed = True
            write_results(r.text, path)
        else:
            print(f"[!] No /server-status in the url")
    except Exception as e:
        print(f"[!] Exception accessing the /server-status path: {e}")
    return succeed

# Write results
def write_results(results, out_file):
    with open(out_file, "a", encoding="utf-8") as f:
        f.write(results)

# Create path for each result
def create_path(folder, name):
    return os.path.join(folder, name)

# Zoomeye search
def zoomeye_search(zm, search, path, stype, rpath):
    time.sleep(1)
    try:
        data = zm.search(search)
        print(f"--- Zoomeye {stype} results ---")
        total_hits = data['total']
        if total_hits > 0:
            print(f"Total results: {total_hits}")
            write_results(f"\n> {stype} results <\n\n", rpath)
            for d in data['data']:
                ip = d['ip']
                print(ip)
                write_results(ip+"\n", rpath)
            write_results(json.dumps(data), path)
    except Exception as e:
        print(f"[!] Exception searching with zoomeye: {e}")

# Shodan search
def shodan_search(api, search, path, stype, rpath):
    try:
        data = api.search(search)
        print(f"--- Shodan {stype} results ---")
        total_hits = data['total']
        if total_hits > 0:
            print(f"Total results: {total_hits}")
            write_results(f"\n> {stype} results <\n\n", rpath)
            for d in data['matches']:
                ip = d['ip_str']
                print(ip)
                write_results(ip+"\n", rpath)
            write_results(json.dumps(data), path)
    except Exception as e:
        print(f"[!] Exception searching with shodan: {e}")

# Modat search
def modat_search(search, path, stype, rpath):
    modat_query = {"query": search,
                   "page": 1,
                   "page_size": 10
                   }
    try:
        r = requests.post(modat_search_url, json=modat_query, headers=modat_headers)
        data = json.loads(r.text)
        print(f"--- Modat {stype} results ---")
        total_hits = data['total_records']
        if total_hits > 0:
            print(f"Total results: {total_hits}")
            write_results(f"\n> {stype} results <\n\n", rpath)
            for d in data['page']:
                ip = d['ip']
                print(ip)
                write_results(ip+"\n", rpath)
            write_results(json.dumps(data), path)
    except Exception as e:
        print(f"[!] Exception searching with modat: {e}")

# Censys search
def censys_search(search, path, stype, rpath):
    censys_search_query = { "query": search }
    try:
        r = requests.post(censys_search_url, json=censys_search_query, headers=censys_headers)
        data = json.loads(r.text)
        print(f"--- Censys {stype} results ---")
        total_hits = data['result']['total_hits']
        if total_hits > 0:
            print(f"Total results: {total_hits}")
            write_results(f"\n> {stype} results <\n\n", rpath)
            for hit in data['result']['hits']:
                if 'host_v1' in hit:
                    ip = hit['host_v1']['resource']['ip']
                    print(ip)
                    write_results(ip+"\n", rpath)
                elif 'webproperty_v1' in hit:
                    for endpoint in hit['webproperty_v1']['resource']['endpoints']:
                        ip = endpoint['ip']
                        print(ip)
                        write_results(ip+"\n", rpath)
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
            else:
                print("[+] Tor connection succesful")
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
        print("[-] Checking TLS...")
        tls = check_tls(domain)
        if (tls != 0):
            url = "https://"+domain
            print(f"[+] TLS hash: {tls}")
            write_results(f"TLS hash: {tls}\n", path)
        else:
            url = "http://"+domain
            print(f"[!] The {domain} do not use TLS")

        # Fetch title
        print("[-] Checking Title...")
        title = fetch_title(url)
        if title:
            print(f"[+] Title: {title}")
            write_results(f"Title: {title}\n", path)

        # Fetch favicon
        print("[-] Checking Favicon...")
        url_favicon = url+"/favicon.ico"
        if fetch_favicon(url_favicon, folder):
            favicon_file = os.path.join(folder, "favicon.ico")
            favicon_hash = generate_favicon_hash(favicon_file)
            print(f"[+] Favicon hash: {favicon_hash}")
            write_results(f"Favicon hash: {favicon_hash}\n", path)

        # Check server-status
        print("[-] Checking server-status url...")
        url_server_status = url+"/server-status"
        server_status_results = os.path.join(folder, "server_status.html")
        server_status = check_server_status(url_server_status, server_status_results)
        if server_status:
            print(f"[+] Server Status available on {domain}/server-status")
            write_results(f"Server status available on: {url}/server-status\n", path)

        if zoomeye_api:
            print(f"\nSearching with Zoomeye...")
            write_results("\n--- Zoomeye Search ---\n", path)
            zm = zoomeye.ZoomEye(api_key=zoomeye_api)
            zoomeye_results = os.path.join(folder, "zoomeye_domain_results.json")
            zoomeye_search(zm, domain, zoomeye_results, "domain", path)
            if tls:
                search = f"ssl.cert.fingerprint=\"{tls}\""
                zoomeye_search(zm, search, zoomeye_results, "tls", path)
            if title:
                search = f"title=\"{title}\""
                zoomeye_search(zm, search, zoomeye_results, "title", path)
            if favicon_hash:
                search = f"iconhash=\"{favicon_hash}\""
                zoomeye_search(zm, search, zoomeye_results, "favicon", path)
        if modat_api:
            print(f"\nSearching with Modat...")
            write_results("\n--- Modat Search ---\n", path)
            # Store domain results
            modat_results = create_path(folder, "modat_domain_results.json")
            modat_search(f"web.html~{domain}", modat_results, "domain", path)
            if tls:
                search = f"cert.fingerprint.sha256={tls}"
                # Store tls results
                modat_results = create_path(folder, "modat_tls_results.json")
                modat_search(search, modat_results, "tls", path)
            if title:
                search = f"web.title~'{title}'"
                # Store title results
                modat_results = create_path(folder, "modat_title_results.json")
                modat_search(search, modat_results, "title", path)
            #if favicon_hash:
            #    search = f"host.services.endpoints.http.favicons.hash_md5:'{favicon_hash}'"
                # Store favicon results
            #    modat_results = create_path(folder, "modat_favicon_results.json")
            #    modat_search(search, modat_results, "favicon", path)
        if censys_token:
            print(f"\nSearching with Censys...")
            write_results("\n--- Censys Search ---\n", path)
            # Store domain results
            censys_results = create_path(folder, "censys_domain_results.json")
            censys_search(f"'{domain}'", censys_results, "domain", path)
            if tls:
                search = f"host.services.tls.fingerprint_sha256:'{tls}'"
                # Store tls results
                censys_results = create_path(folder, "censys_tls_results.json")
                censys_search(search, censys_results, "tls", path)
            if title:
                search = f"host.services.endpoints.http.html_title: '{title}'"
                # Store title results
                censys_results = create_path(folder, "censys_title_results.json")
                censys_search(search, censys_results, "title", path)
            if favicon_hash:
                search = f"host.services.endpoints.http.favicons.hash_md5:'{favicon_hash}'"
                # Store favicon results
                censys_results = create_path(folder, "censys_favicon_results.json")
                censys_search(search, censys_results, "favicon", path)
        if shodan_api:
            api = shodan.Shodan(shodan_api)
            print(f"\nSearching with Shodan...")
            write_results("\n--- Shodan Search ---\n", path)
            shodan_results = create_path(folder, "shodan_domain_results.json")
            shodan_search(api, domain, shodan_results, "domain", path)
            if tls:
                search = f"ssl.cert.fingerprint:{tls}"
                shodan_search(api, search, shodan_results, "tls", path)
            if title:
                search = f"title:'{title}'"
                shodan_search(api, search, shodan_results, "title", path)
            if favicon_hash:
                search = f"http.favicon.hash:'{favicon_hash}'"
                shodan_search(api, search, shodan_results, "favicon", path)

        print(f"\nFinished, check results inside {folder}")
    else:
        parser.print_help()
