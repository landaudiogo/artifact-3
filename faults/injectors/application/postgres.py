#! python3

from psycopg2 import sql
from threading import Lock

import click
import time
import psycopg2
import signal

TERMINATE_MUTEX=Lock()
TERMINATE=False

def signal_handler(sig, frame):
    global TERMINATE
    print(f"Handling signal {sig}: terminating")
    with TERMINATE_MUTEX:
        TERMINATE=True

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

@click.command()
@click.option("--host", required=False, default="127.0.0.1", show_default=True, help="Postgres host address")
@click.option("--port", required=False, default="5432", show_default=True, help="Postgres port")
@click.option("--user", required=True, help="Postgres user")
@click.option("--password", required=True, help="Postgres password")
@click.option("--database", required=True, help="Database to connect to")
@click.option("--table", required=True, help="Table to contend for")
@click.option("--lock-duration", required=False, default="0.1", help="Amount of time to hold the exclusive table lock for")
@click.option("--interval", required=False, default="0.9", help="Time in-between two consecutive lock contention periods")
def postgres_lock_contention(
    host,
    port,
    user,
    password,
    database,
    table,
    lock_duration,
    interval,
):
    global TERMINATE
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=database,
    )
    conn.autocommit = False
    with conn.cursor() as cur:
        while True:
            with TERMINATE_MUTEX:
                if TERMINATE == True:
                    break
            cur.execute("BEGIN;")
            cur.execute(
                f"LOCK TABLE {table} IN ACCESS EXCLUSIVE MODE"
            )
            cur.execute(
                "SELECT pg_sleep(%s);",
                (lock_duration,),
            )
            conn.commit()
            time.sleep(float(interval))

postgres_lock_contention()
