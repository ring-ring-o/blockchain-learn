import logging
import re
import socket

from models import Block

logger = logging.getLogger(__name__)
RE_IP = re.compile(
    r"(?P<prefix_host>^\d{1,3}\.\d{1.3}\.\d{1,3}\.)(?P<last_ip>\d{1,3}$)"
)


def pprint(chains: list[Block]) -> None:
    for index, chain in enumerate(chains):
        print(f"{"="*25} Chain {index} {"="*25}")
        for key, value in chain.model_dump().items():
            print(f"{key:15}{value}")
    print(f"{"*"*25}")


def is_found_host(target: str, port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:
            sock.connect((target, port))
            return True
        except Exception as ex:
            logger.error(
                {
                    "action": "is_found_host",
                    "target": target,
                    "port": port,
                    "ex": str(ex),
                }
            )
            return False


def find_neighbours(
    my_host,
    my_port,
    start_ip_range,
    end_ip_range,
    start_port,
    end_port,
):
    address = f"{my_host}:{my_port}"
    m = RE_IP.search(my_host)
    if not m:
        return None

    prefix_host = m.group("prefix_host")
    last_ip = m.group("last_ip")

    neighbours = []
    for guess_port in range(start_port, end_port):
        for ip_range in range(start_ip_range, end_ip_range):
            guess_host = f"{prefix_host}{int(last_ip) + int(ip_range)}"
            guess_address = f"{guess_host}:{guess_port}"
            if is_found_host(guess_host, guess_port) and not guess_address == address:
                neighbours.append(guess_address)

    return neighbours


def get_host() -> str:
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception as ex:
        logger.error("action: get_host}", str(ex))
        return "127.0.0.1"
