#!/usr/bin/env python3
# pstsrg.py - Process and store logs in a SQLite database, encrypting the database.     02/26/2026
import os
import sqlite3
import sys
import sysprofile
import traceback
from collections import defaultdict
from gpgcrypto import decr
from gpgcrypto import encr
from hanlyparallel import hanly_parallel
from rntchangesfunctions import cnc
from rntchangesfunctions import name_of
from rntchangesfunctions import removefile
from pyfunctions import cprint
from pyfunctions import unescf_py
from query import blank_count
from pysql import collision
from pysql import create_db
from pysql import create_table
from pysql import insert
from pysql import insert_if_not_exists
from pysql import table_has_data


count = 0


def collision_check(xdata, cerr, c, ps):
    reported = set()
    csum = False
    colcheck = collision(c, ps)

    if colcheck:

        collision_map = defaultdict(set)
        for a_filename, b_filename, file_hash, size_a, size_b in colcheck:
            collision_map[a_filename, file_hash].add((b_filename, file_hash, size_a, size_b))
            collision_map[b_filename, file_hash].add((a_filename, file_hash, size_b, size_a))
        try:
            with open(cerr, "a", encoding="utf-8") as f:
                for record in xdata:
                    filename = record[1]
                    checks = record[5]
                    size_non_zero = record[6]
                    if size_non_zero:
                        key = (filename, checks)
                        if key in collision_map:
                            for other_file, file_hash, size1, size2 in collision_map[key]:
                                pair = tuple(sorted([filename, other_file]))
                                if pair not in reported:
                                    csum = True
                                    print(f"COLLISION: {filename} {size1} vs {other_file} {size2} | Hash: {file_hash}", file=f)
                                    reported.add(pair)
        except IOError as e:
            print(f"Failed to write collisions: {e} {type(e).__name__}  \n{traceback.format_exc()}")
    return csum


def main(dbtarget, xdata, COMPLETE, user_setting, logging_values, rout, scr, cerr, dcr=False):

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
            return 2
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
            return 1
        conn = sqlite3.connect(dbopt)
    with conn:
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

                    except Exception as e:
                        print(f'sys db failed insert {e}  {type(e).__name__} \n{traceback.format_exc()}')
                        db_error = True

            elif ps:
                print('Sys profile requires the setting checksum to index')

        # Log
        if xdata:

            if goahead:  # Hybrid analysis. Skip first pass ect.

                try:

                    csum = hanly_parallel(rout, scr, cerr, mMODE, xdata, ANALYTICSECT, checksum, cdiag, dbopt, is_ps, user, logging_values)

                except Exception as e:
                    print(f"hanlydb failed to process on mode {mMODE}: {e} {traceback.format_exc()}", file=sys.stderr)

            try:

                parsed = []
                for record in xdata:
                    parsed.append(record[:16])  # trim esc_path from end

                insert(parsed, conn, c, "logs", ['hardlinks', 'mtime_us'])

                count = blank_count(c)
                if count % 10 == 0:
                    print(f'{count + 1} searches in gpg database')

            except Exception as e:
                print(f'log db failed insert err: {e} {type(e).__name__}  \n{traceback.format_exc()}')
                db_error = True

            # Check for hash collisions
            if checksum and cdiag:
                if collision_check(xdata, cerr, c, ps):
                    csum = True

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

    if not db_error:  # Encrypt if o.k.
        try:

            nc = cnc(dbopt, compLVL)
            sts = encr(dbopt, dbtarget, email, no_compression=nc, dcr=dcr)
            if not sts:
                res = 3  # & 2 gpg problem
                print(f'Failed to encrypt database. Run   gpg --yes -e -r {email} -o {dbtarget} {dbopt}  before running again to preserve data.')

        except Exception as e:
            res = 3
            print(f'Encryption failed: {e}')

    else:
        res = 4  # delete any changes made.
        print('There is a problem with the database.')

    if (dcr and res != 3) or not dcr:
        removefile(dbopt)
    if res == 0 and new_profile:
        return "new_profile"
    elif res == 0:
        return 0
        # return dbopt
    elif res == 3:
        return "encr_error"
    return None
