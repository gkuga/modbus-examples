# Simulated power meter (Modbus TCP server)
# A house with solar panels: active power goes negative while exporting.
# See README.md for the register map.

import asyncio
import random
import time

from pymodbus.client import ModbusTcpClient
from pymodbus.server import StartAsyncTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice

HOST = "127.0.0.1"
PORT = 5020
DEVICE_ID = 1
TIME_SCALE = 60  # 1 real second = 1 simulated minute, so energy grows visibly

FC_READ_DISCRETE_INPUTS = 0x02
FC_READ_HOLDING_REGISTERS = 0x03
FC_READ_INPUT_REGISTERS = 0x04
FC_WRITE_COILS = (0x05, 0x0F)
FC_WRITE_HOLDING_REGISTERS = (0x06, 0x10)

convert_to_registers = ModbusTcpClient.convert_to_registers
DATATYPE = ModbusTcpClient.DATATYPE


class Meter:
    """Internal state of the meter, independent of Modbus."""

    def __init__(self):
        self.relay_on = True
        self.threshold_w = 1000
        self.energy_wh = 123456.0  # larger than 65535 on purpose: needs 32 bits
        self.power_w = 0
        self.last_update = time.monotonic()

    def update(self):
        now = time.monotonic()
        load_w = random.randint(700, 1300) if self.relay_on else 0
        solar_w = random.randint(550, 650)
        self.power_w = load_w - solar_w  # negative = exporting to the grid
        if self.power_w > 0:
            self.energy_wh += self.power_w * (now - self.last_update) * TIME_SCALE / 3600
        self.last_update = now

    def input_registers(self) -> list[int]:
        voltage_v = random.uniform(99.0, 102.0)
        power_factor = random.uniform(0.95, 0.99)
        current_a = abs(self.power_w) / (voltage_v * power_factor)
        frequency_hz = random.uniform(49.95, 50.05)
        return (
            [
                round(voltage_v * 10),  # 0: UINT16, x0.1 V
                round(current_a * 100),  # 1: UINT16, x0.01 A
                self.power_w & 0xFFFF,  # 2: INT16 (two's complement), 1 W
                round(power_factor * 1000),  # 3: UINT16, x0.001
            ]
            # 4-5: FLOAT32, high word first
            + convert_to_registers(frequency_hz, DATATYPE.FLOAT32)
            # 6-7: UINT32, LOW word first (a common vendor quirk)
            + convert_to_registers(
                int(self.energy_wh), DATATYPE.UINT32, word_order="little"
            )
        )


meter = Meter()


async def on_access(function_code, start_address, address, count, registers, values):
    """Called by pymodbus before every register access (see SimDevice.action)."""
    if function_code == FC_READ_INPUT_REGISTERS:
        meter.update()
        registers[:8] = meter.input_registers()
    elif function_code == FC_READ_DISCRETE_INPUTS:
        meter.update()
        # bit blocks are packed 16 bits per register, bit 0 = discrete input 0
        registers[0] = 1 if meter.power_w > meter.threshold_w else 0
    elif function_code == FC_READ_HOLDING_REGISTERS:
        registers[1] = 0  # the reset register always reads as 0
    elif values is None:
        # pymodbus also calls this with values=None when it reads back after a write
        pass
    elif function_code in FC_WRITE_COILS and address == 0:
        meter.relay_on = values[0]
    elif function_code in FC_WRITE_HOLDING_REGISTERS:
        for offset, value in enumerate(values):
            if address + offset == 0:
                meter.threshold_w = value
            elif address + offset == 1 and value == 1:
                meter.energy_wh = 0
    return None


def trace_packet(sending: bool, data: bytes) -> bytes:
    print(f"{'TX' if sending else 'RX'}: {data.hex(' ')}")
    return data


async def main():
    device = SimDevice(
        id=DEVICE_ID,
        # 4 separate tables: (coils, discrete inputs, holding registers, input registers)
        simdata=(
            [SimData(0, values=[True], datatype=DataType.BITS)],
            [SimData(0, values=[False], datatype=DataType.BITS)],
            [SimData(0, values=[meter.threshold_w, 0], datatype=DataType.UINT16)],
            [SimData(0, count=8, values=0, datatype=DataType.UINT16)],
        ),
        action=on_access,
    )

    print(f"power meter listening on {HOST}:{PORT}, device id {DEVICE_ID}")
    await StartAsyncTcpServer(
        context=device, address=(HOST, PORT), trace_packet=trace_packet
    )


if __name__ == "__main__":
    asyncio.run(main())
