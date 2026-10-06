# Hello world Modbus RTU server (slave)
# Holding registers 0-6 hold the string "Hello, Modbus!" (2 ASCII chars per register).

import asyncio

from pymodbus.server import StartAsyncSerialServer
from pymodbus.simulator import DataType, SimData, SimDevice

PORT = "ttyV0"  # created by virtual_serial.py; use e.g. /dev/tty.usbserial-XXXX for real hardware
BAUDRATE = 9600
DEVICE_ID = 1  # slave address of this server
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

    print(f"listening on {PORT} ({BAUDRATE} 8N1), device id {DEVICE_ID}")
    await StartAsyncSerialServer(
        context=device,
        port=PORT,
        baudrate=BAUDRATE,
        bytesize=8,
        parity="N",
        stopbits=1,
        trace_packet=trace_packet,
    )


if __name__ == "__main__":
    asyncio.run(main())
