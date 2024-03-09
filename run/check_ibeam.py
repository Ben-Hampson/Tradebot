"""Check IBeam is running and authenticated."""

import easyib  # type: ignore
import os
import time
import logging
import requests

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


def main():
    IBEAM_HOST = os.getenv("IBEAM_HOST", "https://ibeam:5000")
    try:
        ib_client = easyib.REST(url=IBEAM_HOST, ssl=False)
    except requests.exceptions.RequestException:
        log.info("Unable to contact IBeam container.")
        return False

    response = ib_client.ping_server()

    authenticated = response["iserver"]["authStatus"]["authenticated"]
    connected = response["iserver"]["authStatus"]["connected"]

    if authenticated and connected:
        log.info("IBeam container is UP and AUTHENTICATED.")
    else:
        log.error("IBeam container is up but not authenticated.", response)

    return authenticated and connected


if __name__ == "__main__":
    healthy = False
    while not healthy:
        log.info("Checking IBeam container health...")
        time.sleep(3)
        healthy = main()
