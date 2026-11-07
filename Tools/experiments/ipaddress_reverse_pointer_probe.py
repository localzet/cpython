"""Reproduce issue gh-91601 without choosing an API contract.

Run: python Tools/experiments/ipaddress_reverse_pointer_probe.py
"""
import ipaddress
import json
import sys


def possible_nibble_zone(network):
    if network.prefixlen % 4:
        return None
    prefix_hex = f"{int(network.network_address):032x}"[:network.prefixlen // 4]
    return ".".join(reversed(prefix_hex)) + (
        ".ip6.arpa" if prefix_hex else "ip6.arpa"
    )


def describe(value):
    actual = value.reverse_pointer
    if isinstance(value, ipaddress.IPv6Interface):
        address, network = value.ip, value.network
    elif isinstance(value, ipaddress.IPv6Network):
        address, network = value.network_address, value
    else:
        address, network = value, None
    return {
        "class": type(value).__name__,
        "input": str(value),
        "current": actual,
        "invalid_slash": "/" in actual,
        "address_pointer": address.reverse_pointer,
        "zone_if_nibble_aligned": (
            possible_nibble_zone(network) if network else None
        ),
    }


def main():
    cases = [
        ipaddress.IPv6Address("2001:db8:1:2:3:4:5::"),
        ipaddress.ip_interface("2001:db8:1:2:3:4:5::/64"),
        ipaddress.ip_network("2001:db8:1:2:3:4:5::/64", strict=False),
        ipaddress.ip_network("2001:db8::/65"),
        ipaddress.ip_interface("fe80::1%eth0/64"),
    ]
    result = [describe(x) for x in cases]
    print(json.dumps({"python": sys.version.split()[0], "cases": result},
                     indent=2))
    assert not result[0]["invalid_slash"]
    assert result[1]["invalid_slash"] and result[2]["invalid_slash"]


if __name__ == "__main__":
    main()
