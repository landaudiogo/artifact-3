#! python3

import enum
import click
import json
import sys

from pathlib import Path

class Action(enum.Enum):
    attack = enum.auto()
    recover = enum.auto()

@click.group()
def cpu_reduce():
    pass

@cpu_reduce.command()
@click.option("--uid", required=True, help="Attack unique identifier. This is usually passed to chaosd to identify the fault injected.")
@click.option("--cgroup", required=True, help="Target cgroup to limit the cgroup's maximum allocatable cpu.")
@click.option("--cpu-max", required=True, help="The maximum CPU share relative to 100,000 we want to limit the target cgroup by.")
@click.option(
    "--chaosd-dir",
    envvar=["CHAOSD_DIR"],
    required=True,
    help="The chaosd directory for data persistence. This is the directory where the information for recovery is stored."
)
def attack(uid, cgroup, cpu_max, chaosd_dir):
    cpumax_path = Path(f"/sys/fs/cgroup/{cgroup}/cpu.max")
    try:
        original_contents = cpumax_path.read_text()
        cpumax_path.write_text(f"{cpu_max} 100000")
    except Exception as e:
        print(f"File {cpumax_path} error: {e}", file=sys.stderr)
        sys.exit(1)

    fault_store = Path(f"{chaosd_dir}") / Path(f"{uid}.recover")
    recover_data = {
        "original_contents": original_contents,
        "cpumax_path": str(cpumax_path),
    }
    with open(fault_store, "w") as f:
        json.dump(recover_data, f)


@cpu_reduce.command()
@click.option("--uid", required=True, help="Attack unique identifier. This is usually passed to chaosd to identify the fault injected.")
@click.option(
    "--chaosd-dir",
    envvar=["CHAOSD_DIR"],
    required=True,
    help="The chaosd directory for data persistence. This is the directory where the information for recovery is stored."
)
def recover(uid, chaosd_dir):
    fault_store = Path(f"{chaosd_dir}") / Path(f"{uid}.recover")
    try:
        with fault_store.open("r") as f:
            recover_data = json.load(f)
    except Exception as e:
        # We've received a uuid that hasn't successfully completed attack
        print(f"Failed to read {fault_store}: {e}", file=sys.stderr)
        sys.exit(1)

    cpumax_path = Path(recover_data["cpumax_path"])
    try:
        cpumax_path.write_text(recover_data["original_contents"])
    except Exception as e:
        # The cgroup no longer exists
        pass

    fault_store.unlink(missing_ok=True)


cpu_reduce()
