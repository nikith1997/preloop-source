#!/home/python/.pyenv/shims/python

import signal
import time


class _Terminate(Exception):
    pass


def _handle_kill(signum, _frame):
    print(f"Term signal received: {signum} - killing process")
    raise _Terminate()


signal.signal(signal.SIGTERM, _handle_kill)

try:
    print("TODO: Run the real entry point")
    for minute in range(1 << 31):
        print(f"Endless Loop {minute} - Ctrl-C or stop container to exit")
        time.sleep(60)

except _Terminate:
    print("Exiting container")
