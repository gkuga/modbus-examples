# Hello world Modbus TCP server
# Holding registers 0-6 hold the string "Hello, Modbus!" (2 ASCII chars per register).

import asyncio

from pymodbus.server import StartAsyncTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice

HOST = "127.0.0.1"
PORT = 5020  # the standard port is 502, but it may need root
DEVICE_ID = 1
MESSAGE = "Hello, Modbus!"


def trace_packet(sending: bool, data: bytes) -> bytes:
    print(f"{'TX' if sending else 'RX'}: {data.hex(' ')}")
    return data


async def main():
    device = SimDevice(
        id=DEVICE_ID,
        simdata=[
            SimData(0, values=MESSAGE, datatype=DataType.STRING),  # registers 0-6
            SimData(7, count=10, values=0, datatype=DataType.UINT16),  # registers 7-16
        ],
    )

    print(f"listening on {HOST}:{PORT}")
    await StartAsyncTcpServer(
        context=device, address=(HOST, PORT), trace_packet=trace_packet
    )


if __name__ == "__main__":
    asyncio.run(main())
