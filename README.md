# Dark Web Deanonimization

Is it possible to try to de-anonimize a domain in the Dark Web, as it's explained on my [talk on RootedCon Valencia](https://github.com/bash-bunny/RootedValencia2025).

The script try the following techniques:
- Search by the domain.
- Check if the webpage use TLS and if so, grab the hash of the certificate and search for it.
- Retrieve the title of the webpage and search for it.
- Retrieve the favicon and search for it.
- Check if the website has the `/server-status` enabled.

## Installation

```bash
# Clone the repository
git clone https://github.com/bash-bunny/dw_deanon.git

# Access the repo directory
cd dw_deanon

# Activate the virtual environment for python
python -m venv venv
. venv/bin/activate
# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create the file `.env` with the following data:

```
ZOOMEYE_KEY="ZOOMEYE-API-KEY"
SHODAN_KEY="SHODAN-API-KEY"
MODAT_KEY="MODAT-API-KEY"
```

For Censys you must follow [their guide](https://censys-python.readthedocs.io/en/stable/quick-start.html)

### Dependencies

#### TOR

You need TOR installed and running on your system on port `9050`. The installation depends on your system, but usually is something like:

```bash
# Debian based
sudo apt install tor
sudo systemctl start tor

# Arch Linux
sudo pacman -S tor
sudo systemctl start tor

# Gentoo
sudo emerge -av net-vpn/tor
sudo rc-service tor start
```

#### APIs

In order to maximize the results you need an API from:
- [Shodan](https://developer.shodan.io)
- [Censys](https://search.censys.io/api)
- [Zoomeye](https://www.zoomeye.ai/)

## Usage

```bash
# Access the repo and activate the virtual environment
cd dw-deanon
. venv/bin/activate

# Show the help
python dw-deanon.py

# Try different techniques to deanonimize a domain
python dw-deanon.py --domain 222222222k5na7udftysk7ytjsvmmr47p2e4zh2cftsaj7qvrts4u3id.onion

# Deactivate the virtual environment
deactivate
```

It creates a folder with the name of the onion domain and store inside that folder the results.
