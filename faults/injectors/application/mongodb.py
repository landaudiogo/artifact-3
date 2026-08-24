#! python3

from threading import Lock
from pymongo import MongoClient
from pymongo.errors import OperationFailure
import click
import time
import signal

TERMINATE_MUTEX = Lock()
TERMINATE = False


def signal_handler(sig, frame):
    global TERMINATE
    print(f"handling signal {sig}: terminating")
    with TERMINATE_MUTEX:
        TERMINATE = True


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


@click.command()
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="MongoDB host address",
)
@click.option(
    "--port",
    default=27017,
    type=int,
    show_default=True,
    help="MongoDB port",
)
@click.option(
    "--user",
    required=False,
    help="MongoDB user",
)
@click.option(
    "--password",
    required=False,
    help="MongoDB password",
)
@click.option(
    "--lock-duration",
    default=0.4,
    type=float,
    show_default=True,
    help="Amount of time to hold the fsync lock (seconds)",
)
@click.option(
    "--interval",
    default=0.6,
    type=float,
    show_default=True,
    help="Time between two consecutive lock contention periods (seconds)",
)
def mongodb_lock_contention(
    host,
    port,
    user,
    password,
    lock_duration,
    interval,
):
    global TERMINATE, TERMINATE_MUTEX

    client = MongoClient(
        host=host,
        port=port,
        username=user,
        password=password,
    )
    admin_db = client.admin

    while True:
        with TERMINATE_MUTEX:
            if TERMINATE:
                break

        try:
            admin_db.command({"fsync": 1, "lock": True})
            print(f"Holding fsync lock for {lock_duration} seconds...")
            time.sleep(lock_duration)
            admin_db.command({"fsyncUnlock": 1})
        except OperationFailure as exc:
            print(f"Mongodb failure: {exc}")
            break

        print(f"Sleeping for {interval} seconds before next contention period...")
        time.sleep(interval)

    client.close()

mongodb_lock_contention()
