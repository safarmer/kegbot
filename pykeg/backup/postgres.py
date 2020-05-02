"""Postgres-specific database backup/restore implementation."""

import logging
import os
import subprocess

from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_DB = "default"

# Common command-line arguments
PARAMS = {
    "db": settings.DATABASES[DEFAULT_DB].get("NAME"),
    "user": settings.DATABASES[DEFAULT_DB].get("USER"),
    "password": settings.DATABASES[DEFAULT_DB].get("PASSWORD"),
    "host": settings.DATABASES[DEFAULT_DB].get("HOST"),
    "port": settings.DATABASES[DEFAULT_DB].get("PORT"),
}

DEFAULT_ARGS = []
if PARAMS.get("user"):
    DEFAULT_ARGS.append("--username={}".format(PARAMS["user"]))
if PARAMS.get("host"):
    DEFAULT_ARGS.append("--host={}".format(PARAMS["host"]))
if PARAMS.get("port"):
    DEFAULT_ARGS.append("--port={}".format(PARAMS["port"]))

DEFAULT_ENV = dict(os.environ)
if PARAMS.get("password"):
    DEFAULT_ENV["PGPASSWORD"] = PARAMS["password"]


def engine_name():
    return "postgres"


def is_installed():
    args = ["psql"] + DEFAULT_ARGS
    args += ["-qt", "-c \"select * from pg_tables where schemaname='public';\"", PARAMS["db"]]
    cmd = " ".join(args)
    logger.info(cmd)
    output = subprocess.check_output(cmd, env=DEFAULT_ENV, shell=True)
    return "core_" in output


def dump(output_fd):
    args = ["pg_dump"] + DEFAULT_ARGS
    args.append(PARAMS["db"])
    cmd = " ".join(args)
    logger.info(cmd)
    return subprocess.check_call(cmd, stdout=output_fd, env=DEFAULT_ENV, shell=True)


def restore(input_fd):
    args = ["psql"] + DEFAULT_ARGS
    args.append(PARAMS["db"])
    cmd = " ".join(args)
    logger.info(cmd)
    return subprocess.check_call(cmd, stdin=input_fd, shell=True)


def erase():
    args = ["psql"] + DEFAULT_ARGS
    args += [PARAMS["db"], "-c 'drop schema public cascade; create schema public;'"]
    cmd = " ".join(args)
    logger.info(cmd)
    subprocess.check_call(cmd, shell=True)
