"""Run read-only Sonos SSDP discovery on the Docker Desktop host's LAN interface."""

import argparse
import json
import socket
import time


def discover(interface, timeout=6):
    message = (
        "M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n"
        'MAN: "ssdp:discover"\r\nMX: 2\r\n'
        "ST: urn:schemas-upnp-org:device:ZonePlayer:1\r\n\r\n"
    )
    found = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.bind((interface, 0))
        sock.settimeout(0.5)
        for _ in range(3):
            sock.sendto(message.encode(), ("239.255.255.250", 1900))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                data, address = sock.recvfrom(65535)
            except socket.timeout:
                continue
            headers = {
                line.partition(":")[0].lower(): line.partition(":")[2].strip()
                for line in data.decode(errors="replace").split("\r\n")[1:]
                if ":" in line
            }
            if "location" in headers:
                found[address[0]] = headers["location"]
    return dict(sorted(found.items(), key=lambda item: socket.inet_aton(item[0])))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interface", required=True, help="Host LAN IPv4 address")
    parser.add_argument("--yaml", action="store_true", help="Print Sonos HA configuration")
    args = parser.parse_args()
    hosts = discover(args.interface)
    if not hosts:
        raise SystemExit("No Sonos SSDP replies; check LAN interface, routing and UPnP")
    if args.yaml:
        print("sonos:\n  media_player:\n    advertise_addr:", args.interface)
        print("    hosts:")
        for host in hosts:
            print("      -", host)
    else:
        print(json.dumps(hosts, indent=2))
