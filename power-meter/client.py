# Power meter client (Modbus TCP)
# Reads raw registers and decodes them by hand according to the register map
# in README.md, then changes settings and watches the effect.

import struct

from pymodbus.client import ModbusTcpClient

HOST = "127.0.0.1"
PORT = 5020
DEVICE_ID = 1


def check(response):
    """Raise if the server returned an exception response (function code | 0x80)."""
    if response.isError():
        raise RuntimeError(f"Modbus exception response: {response}")
    return response


def to_int16(reg: int) -> int:
    """Interpret a 16-bit register as a signed (two's complement) value."""
    return reg - 0x10000 if reg & 0x8000 else reg


def to_uint32(high: int, low: int) -> int:
    return (high << 16) | low


def to_float32(high: int, low: int) -> float:
    return struct.unpack(">f", struct.pack(">HH", high, low))[0]


def show_measurements(client: ModbusTcpClient):
    regs = check(client.read_input_registers(0, count=8, device_id=DEVICE_ID)).registers
    print("  raw input registers 0-7:")
    print("    " + "  ".join(f"[{i}]={r:5d} (0x{r:04x})" for i, r in enumerate(regs[:4])))
    print("    " + "  ".join(f"[{i}]={r:5d} (0x{r:04x})" for i, r in enumerate(regs[4:], 4)))

    print("  decoded:")
    print(f"    30001     voltage      UINT16 x0.1   -> {regs[0] * 0.1:.1f} V")
    print(f"    30002     current      UINT16 x0.01  -> {regs[1] * 0.01:.2f} A")
    print(f"    30003     power        INT16         -> {to_int16(regs[2])} W"
          f"  (as UINT16 it would be {regs[2]})")
    print(f"    30004     power factor UINT16 x0.001 -> {regs[3] * 0.001:.3f}")
    print(f"    30005-06  frequency    FLOAT32       -> {to_float32(regs[4], regs[5]):.2f} Hz")
    energy = to_uint32(high=regs[7], low=regs[6])  # this meter sends the low word first
    wrong = to_uint32(high=regs[6], low=regs[7])
    print(f"    30007-08  energy       UINT32 (low word first) -> {energy} Wh"
          f"  (wrong word order would give {wrong})")


def show_status(client: ModbusTcpClient):
    relay = check(client.read_coils(0, count=1, device_id=DEVICE_ID)).bits[0]
    alarm = check(client.read_discrete_inputs(0, count=1, device_id=DEVICE_ID)).bits[0]
    threshold = check(client.read_holding_registers(0, count=1, device_id=DEVICE_ID)).registers[0]
    print(f"  00001 relay={'ON' if relay else 'OFF'}"
          f"  10001 alarm={'ACTIVE' if alarm else 'off'}"
          f"  40001 threshold={threshold} W")


def main():
    client = ModbusTcpClient(HOST, port=PORT)
    client.connect()

    print("1. Read measurements (input registers, function code 0x04)")
    show_measurements(client)

    print("\n2. Read status (coil 0x01, discrete input 0x02, holding register 0x03)")
    show_status(client)

    print("\n3. Lower the alarm threshold to 0 W (write holding register, 0x06)")
    check(client.write_register(0, 0, device_id=DEVICE_ID))
    show_status(client)

    print("\n4. Turn the relay OFF (write coil, 0x05): no load, only solar export")
    check(client.write_coil(0, False, device_id=DEVICE_ID))
    show_measurements(client)
    show_status(client)

    print("\n5. Restore settings (write multiple holding registers 0x10, write coil 0x05)")
    check(client.write_registers(0, [1000, 0], device_id=DEVICE_ID))
    check(client.write_coil(0, True, device_id=DEVICE_ID))
    show_measurements(client)
    show_status(client)

    client.close()


if __name__ == "__main__":
    main()
