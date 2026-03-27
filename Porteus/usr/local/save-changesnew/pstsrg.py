#!/usr/bin/env python3
# pstsrg.py - Process and store logs in a SQLite database, encrypting the database.     03/25/2026
import os
import sqlite3
import sys
import sysprofile
import traceback
from gpgcrypto import decr
from gpgcrypto import encr
from hanlyparallel import hanly_parallel
from rntchangesfunctions import cnc
from rntchangesfunctions import name_of
from rntchangesfunctions import removefile
from pyfunctions import cprint
from pyfunctions import unescf_py
from pysql import blank_count
from pysql import create_db
from pysql import create_table
from pysql import insert
from pysql import insert_if_not_exists
from pysql import table_has_data
from pysql import collision_check


def main(dbtarget, xdata, COMPLETE, user_setting, logging_values, rout, scr, cerr, cachermPATTERNS, dcr=False):

    user = user_setting['USR']
    email = user_setting['email']
    mMODE = user_setting['mMODE']
    ANALYTICSECT = user_setting['ANALYTICSECT']
    checksum = user_setting['checksum']
    cdiag = user_setting['cdiag']
    ps = user_setting['ps']
    compLVL = user_setting['compLVL']

    parsedsys = []

    outfile = name_of(dbtarget, '.db')
    sys_table = "sys"

    csum = False
    new_profile = False
    db_error = False
    goahead = True
    is_ps = False
    conn = None

    res = 0

    # original with a temp dir cant leave db to reencrypt if everything succeeds but only reencryption fails. so leave in app directory with proper perms
    # TEMPDIR = tempfile.gettempdir()
    # TEMPDIR = tempfile.mkdtemp()
    # os.makedirs(TEMPDIR, exist_ok=True)
    # with tempfile.TemporaryDirectory(dir=TEMPDIR) as mainl:
    # dbopt = name_of(dbtarget, 'db')   # generic output database
    # with tempfile.TemporaryDirectory(dir='/tmp') as tempdir:
    #     dbopt = os.path.join(tempdir, dbopt)

    # app_dir = os.path.dirname(dbtarget)
    app_dir = logging_values[2]
    dbopt = os.path.join(app_dir, outfile)

    if os.path.isfile(dbtarget):
        sts = decr(dbtarget, dbopt)
        if not sts:
            if sts is None:
                print(f"pstsrg unable to do hybrid analysis No key for {dbtarget} delete it to make a new one.")
            return 2, csum
    else:
        try:
            conn = create_db(dbopt, True)
            cprint.green('Persistent database created')
            goahead = False
        except Exception as e:
            print("Failed to create db:", e)
    if not conn:
        if not os.path.isfile(dbopt):
            print("pstsrg.py couldnt locate database: ", dbopt, " quiting.")
            return 1, csum
        conn = sqlite3.connect(dbopt)

    try:
        c = conn.cursor()

        if table_has_data(conn, sys_table):
            is_ps = True
        else:
            # initial Sys profile
            if ps and checksum:

                create_table(c, sys_table, ('timestamp', 'filename', 'changetime', 'checksum'), ['count INTEGER', 'mtime_us INTEGER'])
                new_profile = True

                try:

                    parsedsys = sysprofile.main(mMODE, logging_values)  # hash base xzms

                except Exception as e:
                    print(f'sysprofile.py failed to hash. {type(e).__name__} {e} \n {traceback.format_exc()} ')
                    parsedsys = None

                if parsedsys:

                    try:

                        insert(parsedsys, conn, c, sys_table, ['count', 'mtime_us'])
                        conn.commit()
                    except Exception as e:
                        print(f'sys db failed insert {e}  {type(e).__name__} \n{traceback.format_exc()}')

            elif ps:
                print('Sys profile requires the setting checksum to index')

        # Log
        if xdata:

            if goahead:  # Hybrid analysis. Skip first pass ect.

                try:

                    csum = hanly_parallel(rout, scr, cerr, mMODE, xdata, cachermPATTERNS, ANALYTICSECT, checksum, cdiag, dbopt, is_ps, user, logging_values)

                except Exception as e:
                    print(f"hanlydb failed to process on mode {mMODE}: {e} {traceback.format_exc()}", file=sys.stderr)

            parsed = []
            for record in xdata:
                parsed.append(record[:16])  # trim esc_path from end

        if parsed:
            try:

                insert(parsed, conn, c, "logs", ['hardlinks', 'mtime_us'])

                count = blank_count(c)
                if count % 10 == 0:
                    print(f'{count + 1} searches in gpg database')

                # Check for hash collisions
                if checksum and cdiag:
                    if collision_check(xdata, cerr, c, ps):
                        csum = True

            except Exception as e:
                print(f'log db failed insert err: {e} {type(e).__name__}  \n{traceback.format_exc()}')
                db_error = True

            if mMODE == 'mc':
                x = os.cpu_count()
                if x:
                    if not csum:
                        print(f'Detected {x} CPU cores.')
        # Stats
        if rout:

            if COMPLETE:  # store no such files
                rout.extend([" ".join(map(str, item)) for item in COMPLETE])
                # rout.extend(" ".join(map(str, item)) for item in COMPLETE)

            try:
                for record in rout:
                    # parts = record.strip().split(None, 5)  # original
                    parts = record.strip().split(maxsplit=5)
                    if len(parts) < 6:
                        continue
                    action = parts[0]
                    timestamp = f'{parts[1]} {parts[2]}'
                    changetime = f'{parts[3]} {parts[4]}'
                    fp_escaped = parts[5]
                    fp = unescf_py(fp_escaped)
                    insert_if_not_exists(action, timestamp, fp, changetime, conn, c)

            except Exception as e:
                print(f'stats db failed to insert err: {e}  \n{traceback.format_exc()}')
                db_error = True

        if not db_error:
            try:
                conn.commit()
                nc = cnc(dbopt, compLVL)
                sts = encr(dbopt, dbtarget, email, no_compression=nc, dcr=dcr)
                if not sts:
                    res = 3  # & 2 gpg problem
                    print(f'Failed to encrypt database. Run   gpg --yes -e -r {email} -o {dbtarget} {dbopt}  before running again to preserve data.')

            except Exception as e:
                res = 3
                print(f'Encryption failed: {e}')

        else:
            conn.rollback()
            res = 4  # delete any changes made.
            print('There is a problem with the database.')
    finally:
        if conn:
            conn.close()

    if (dcr and res != 3) or not dcr:
        removefile(dbopt)

    if res == 0 and new_profile:
        return "new_profile", csum
    elif res == 0:
        return 0, csum
        # return dbopt
    elif res == 3:
        return "encr_error", csum
    elif res == 4:
        return "db_error", csum
    return res, csum
