#!/usr/bin/env python3
import logging
import os
import sqlite3
import sys
import sysprofile
from pathlib import Path
from query import activateps
from pyfunctions import setup_logger
from rntchangesfunctions import update_config


def main(appdata_local, tempdir, database, target, config_file, email, ll_level, turbo, compLVL):

    parsed_sys = []

    compLVL = int(compLVL)
    appdata_local = Path(appdata_local)
    tempdir = Path(tempdir)

    logging_values = (appdata_local, ll_level, tempdir)
    setup_logger(logging_values[1], "HASHPROFILE", logging_values[0])

    if os.path.isfile(database):
        try:

            with sqlite3.connect(database) as conn:
                cur = conn.cursor()

                parsed_sys = sysprofile.main(turbo, logging_values)

                # process results
                if parsed_sys:

                    if activateps(parsed_sys, database, target, conn, cur, email, compLVL):

                        update_config(config_file, "proteusSHIELD", "false")

                        return 0
                    else:
                        print("hash_profile.py Failed to insert profile into db")
                else:
                    print(f"System profile failed in {logging_values[0]}/sysprofile")

        except sqlite3.Error as e:
            print(f"hash_profile.py SQLite error: {e}")
            logging.error("SQLite error in hash_profile.py", exc_info=True)
        except Exception as e:
            print(f"hash_profile.py Unexpected error: {e} {type(e).__name__}")
            logging.error(f"hash_profile.py Unexpected error: {e} {type(e).__name__}", exc_info=True)  # \n {traceback.format_exc()}

    else:
        print("hash_profile.py could not find dbopt: ", database)

    return 1


if __name__ == "__main__":
    if len(sys.argv) < 10:
        print("Usage: hash_profile.py <ppdata_local> <tempdir> <database> <target> <config_file> <email> <ll_level> <turbo> <compLVL>")
        sys.exit(0)

    sys.exit(main(*sys.argv[1:10]))
