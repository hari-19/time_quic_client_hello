import argparse
import asyncio
import logging
import pickle
import ssl
import struct
import socket
from typing import Optional, cast

from aioquic.asyncio.client import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.logger import QuicFileLogger
from multiprocessing import Process
from aioquic.quic.connection import QuicConnectionState

import time

logger = logging.getLogger("client")

class DosClientProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream_id = None

    async def send(self, d) -> None:
        data = str(d).encode()

        if self.stream_id == None:
            self.stream_id = self._quic.get_next_available_stream_id()
        self._quic.send_stream_data(self.stream_id, data, end_stream=False)
        self.transmit()

        return

def save_session_ticket(ticket):
    """
    Callback which is invoked by the TLS engine when a new session ticket
    is received.
    """
    logger.info("New session ticket received")


async def main(
    host: str,
    port: int,
) -> None:
    logger.debug(f"Connecting to {host}:{port}")
    i = 0
    with open("time_client_hello.csv", "w") as file:
        file.write("Total Time,Init Time,Write to crypto stream,\n")

    while(i < 1000):
        i += 1
        print("Starting a connection")
        try:
            configuration = QuicConfiguration(alpn_protocols=["dos-demo"], is_client=True)
            configuration.verify_mode = ssl.CERT_NONE
            async with connect(
                host,
                port,
                configuration=configuration,
                session_ticket_handler=save_session_ticket,
                create_protocol=DosClientProtocol,
                local_port=0
            ) as client:
                client = cast(DosClientProtocol, client)

                # Send a message
                await client.send("Hello World")
                
                await client.wait_closed()
        except ConnectionError:
            print("EXCEPTION: Connection Error")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QUIC DOS Demo")
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="The remote peer's host name or IP address",
    )
    parser.add_argument(
        "--port", type=int, default=853, help="The remote peer's port number"
    )
    
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="increase logging verbosity"
    )

    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    
    asyncio.run(
            main(
                host=args.host,
                port=args.port,
        )
    )