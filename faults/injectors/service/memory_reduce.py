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
def memory_reduce():
    pass

@memory_reduce.command()
@click.option("--uid", required=True, help="Attack unique identifier. This is usually passed to chaosd to identify the fault injected.")
@click.option("--cgroup", required=True, help="Target cgroup to limit the cgroup's maximum allocatable memory.")
@click.option("--memory-max", required=True, help="The maximum allocatable memory in bytes")
@click.option(
    "--chaosd-dir",
    envvar=["CHAOSD_DIR"],
    required=True,
    help="The chaosd directory for data persistence. This is the directory where the information for recovery is stored."
)
def attack(uid, cgroup, memory_max, chaosd_dir):
    memory_max_path = Path(f"/sys/fs/cgroup/{cgroup}/memory.max")
    try:
        original_contents = memory_max_path.read_text()
        memory_max_path.write_text(f"{memory_max}")
    except Exception as e:
        print(f"File {memory_max_path} error: {e}", file=sys.stderr)
        sys.exit(1)

    fault_store = Path(f"{chaosd_dir}") / Path(f"{uid}.recover")
    recover_data = {
        "original_contents": original_contents,
        "memory_max_path": str(memory_max_path),
    }
    with open(fault_store, "w") as f:
        json.dump(recover_data, f)


@memory_reduce.command()
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

    memory_max_path = Path(recover_data["memory_max_path"])
    try:
        memory_max_path.write_text(recover_data["original_contents"])
    except Exception as e:
        # The cgroup no longer exists
        pass

    fault_store.unlink(missing_ok=True)


memory_reduce()
