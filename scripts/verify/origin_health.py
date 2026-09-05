"""Independent, read-only origin/connector and external provider-edge probes."""
import argparse
import ipaddress
import json
import urllib.error
import urllib.request
from urllib.parse import urlsplit


def probe(url: str, *, edge: bool) -> str:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return 'healthy' if edge or response.status == 200 else 'failed'
    except urllib.error.HTTPError:
        # Receiving a certificate-validated HTTP response proves edge reachability,
        # even when the application or connector below it is unavailable.
        return 'healthy' if edge else 'failed'
    except (urllib.error.URLError, OSError):
        return 'unknown'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layer', choices=['edge', 'origin_connector'], required=True)
    parser.add_argument('--url', help='Published provider HTTPS hostname for edge; loopback /ready for connector')
    parser.add_argument('--confirm-external', action='store_true')
    parser.add_argument('--confirm-origin', action='store_true')
    args = parser.parse_args()
    url = args.url or 'http://127.0.0.1:20241/ready'
    parsed = urlsplit(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        parser.error('credential-free URL without query or fragment required')
    if args.layer == 'edge':
        if not args.confirm_external or not args.url or parsed.scheme != 'https':
            parser.error('edge requires --confirm-external and the provider HTTPS URL')
    else:
        try:
            loopback = ipaddress.ip_address(parsed.hostname or '').is_loopback
        except ValueError:
            loopback = False
        if not args.confirm_origin or not loopback or parsed.path != '/ready':
            parser.error('connector requires --confirm-origin and a loopback /ready URL')
    state = probe(url, edge=args.layer == 'edge')
    print(json.dumps({'layer': args.layer, 'state': state}))
    return 0 if state == 'healthy' else 1


if __name__ == '__main__':
    raise SystemExit(main())
