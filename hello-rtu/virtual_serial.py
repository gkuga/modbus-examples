# Virtual null-modem cable for testing Modbus RTU without hardware.
# Creates two pseudo terminals linked to ./ttyV0 and ./ttyV1;
# bytes written to one come out of the other (like `socat pty pty`).

import os
import pty
import select
import signal
import tty

LINKS = ["ttyV0", "ttyV1"]


def main():
    # clean up the links on Ctrl-C and on kill
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, signal.default_int_handler)

    masters = []
    for link in LINKS:
        master, slave = pty.openpty()
        tty.setraw(slave)
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(os.ttyname(slave), link)
        masters.append(master)
        print(f"{link} -> {os.ttyname(slave)}")

    peer = {masters[0]: masters[1], masters[1]: masters[0]}
    try:
        while True:
            readable, _, _ = select.select(masters, [], [])
            for fd in readable:
                try:
                    os.write(peer[fd], os.read(fd, 1024))
                except OSError:
                    # nobody has the other end open yet
                    pass
    except KeyboardInterrupt:
        pass
    finally:
        for link in LINKS:
            os.remove(link)


if __name__ == "__main__":
    main()
