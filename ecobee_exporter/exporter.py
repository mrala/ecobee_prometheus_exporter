import argparse
import http.server
import logging
import os
import sys

import prometheus_client

import ecobee_exporter


def main():
    parser = argparse.ArgumentParser("Ecobee Exporter")

    parser.add_argument("--port", type=int, default=os.environ.get('PORT', 9756))
    parser.add_argument("--bind_address", default=os.environ.get("BIND", "0.0.0.0"))
    parser.add_argument("--api_key", default=os.environ.get('APIKEY'))
    parser.add_argument("--auth_file", default=os.environ.get('AUTH','pyecobee_db'))
    parser.add_argument("--verbose", "-v", action="count")

    args = parser.parse_args()

    if args.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(stream=sys.stdout, level=level)

    collector = ecobee_exporter.EcobeeCollector(args.api_key, args.auth_file)

    prometheus_client.REGISTRY.register(collector)

    handler = prometheus_client.MetricsHandler.factory(
        prometheus_client.REGISTRY)
    server = http.server.HTTPServer(
        (args.bind_address, args.port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info('Shutting down server...')
        server.shutdown()
