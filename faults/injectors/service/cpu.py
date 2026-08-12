#! python3

import enum
import click
import subprocess
import json
import os
import sys
import signal

from pathlib import Path

class Action(enum.Enum):
    attack = enum.auto()
    recover = enum.auto()

@click.group()
def cpu_stress():
    pass

@cpu_stress.command()
@click.option("--uid", required=True, help="Attack unique identifier. This is usually passed to chaosd to identify the fault injected.")
@click.option("--cgroup", required=True, help="Target cgroup where the cpu-stress fault will run.")
@click.option("--cpu-max", required=True, help="The maximum CPU share relative to 100,000 we want to limit the target cgroup by.")
@click.option(
    "--chaosd-dir",
    envvar=["CHAOSD_DIR"],
    required=True,
    help="The chaosd directory for data persistence. This is the directory where the information for recovery is stored."
)
def attack(uid, cgroup, cpu_max, chaosd_dir):
    # Attack expects depends on cgexec and stress-ng to be available in its $PATH
    cpumax_path = Path(f"/sys/fs/cgroup/{cgroup}/cpu.max")
    original_contents = cpumax_path.read_text()
    cpumax_path.write_text(f"{cpu_max} 100000")

    log_file = Path(f"{chaosd_dir}") / Path(f"{uid}.log")
    with log_file.open("ab") as log:
        child = subprocess.Popen(
            ["cgexec", "-g" f":{cgroup}", "stress-ng", "--cpu", "2", "-l", "50"],
            stdout=log,
            stderr=log,
            stdin=subprocess.DEVNULL,
        )

    fault_store = Path(f"{chaosd_dir}") / Path(f"{uid}.recover")
    recover_data = {
        "pid": child.pid,
        "original_contents": original_contents,
        "cpumax_path": str(cpumax_path),
    }
    with open(fault_store, "w") as f:
        json.dump(recover_data, f)

@cpu_stress.command()
@click.option("--uid", required=True, help="Attack unique identifier. This is usually passed to chaosd to identify the fault injected.")
@click.option(
    "--chaosd-dir",
    envvar=["CHAOSD_DIR"],
    required=True,
    help="The chaosd directory for data persistence. This is the directory where the information for recovery is stored."
)
def recover(uid, chaosd_dir):
    fault_store = Path(f"{chaosd_dir}") / Path(f"{uid}.recover")
    with fault_store.open("r") as f:
        recover_data = json.load(f)

    try:
        os.kill(recover_data["pid"], signal.SIGTERM)
    except Exception as e:
        print(f"Failed to kill process with pid {recover_data['pid']}: {e}", file=sys.stderr)

    cpumax_path = Path(recover_data["cpumax_path"])
    try:
        cpumax_path.write_text(recover_data["original_contents"])
    except Exception as e:
        print(f"Failed to restore cpumax_path original_contents: {e}", file=sys.stderr)

    fault_store.unlink(missing_ok=True)

cpu_stress()
