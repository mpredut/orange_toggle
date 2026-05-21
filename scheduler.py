import time
import datetime
import subprocess
import os

BASE_DIR = "/home/marius/orange_toggle"
PYTHON = f"{BASE_DIR}/venv/bin/python"
SCRIPT = f"{BASE_DIR}/orange_internet.py"
LOG = f"{BASE_DIR}/orange.log"

CHECK_INTERVAL = 60  # secunde

last_state = None  # "enable" sau "disable"


def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")


def run_command(action):
    global last_state

    if last_state == action:
        return  # nu face nimic dacă e deja în starea corectă

    try:
        subprocess.run(
            [PYTHON, SCRIPT, action],
            cwd=BASE_DIR,
            stdout=open(LOG, "a"),
            stderr=subprocess.STDOUT,
        )
        log(f"Executed: {action}")
        last_state = action
    except Exception as e:
        log(f"Error running {action}: {e}")


def get_desired_state():
    hour = datetime.datetime.now().hour

    if hour >= 23 or hour < 5:
        return "disable"
    else:
        return "enable"


def main():
    log("=== Service started ===")

    while True:
        try:
            desired = get_desired_state()
            run_command(desired)
        except Exception as e:
            log(f"Loop error: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
