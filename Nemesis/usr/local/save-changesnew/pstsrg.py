#!/usr/bin/env python3
# pstsrg.py - Process and store logs in a SQLite database, encrypting the database.     01/09/2026
import os
import sqlite3
import sys
import sysprofile
import traceback
from hanlyparallel import hanly_parallel
from rntchangesfunctions import getnm
from rntchangesfunctions import intst
from rntchangesfunctions import decr
from rntchangesfunctions import encr
from rntchangesfunctions import removefile
from pyfunctions import ccheck
from pyfunctions import unescf_py
from pyfunctions import getcount
from pyfunctions import cprint

count = 0


def table_has_data(conn, table_name):
    c = conn.cursor()
    c.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table_name,))
    if not c.fetchone():
        c.close()
        return False
    c.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
    res = c.fetchone() is not None
    c.close()
    return res


def create_table(c, table, unique_columns, e_cols=None):
    columns = [
        'id INTEGER PRIMARY KEY AUTOINCREMENT',
        'timestamp TEXT',
        'filename TEXT',
        'changetime TEXT',
        'inode TEXT',
        'accesstime TEXT',
        'checksum TEXT',
        'filesize INTEGER',
        'symlink TEXT',
        'owner TEXT',
        '`group` TEXT',
        'permissions TEXT',
        'casmod TEXT',
        'lastmodified TEXT'
    ]
    if e_cols:
        if isinstance(e_cols, str):
            e_cols = [col.strip() for col in e_cols.split(',') if col.strip()]
        columns += e_cols

    col_str = ',\n      '.join(columns)
    unique_str = ', '.join(unique_columns)
    sql = f'''
    CREATE TABLE IF NOT EXISTS {table} (
    {col_str},
    UNIQUE({unique_str})
    )
    '''
    c.execute(sql)

    sql = 'CREATE INDEX IF NOT EXISTS'

    if table == 'logs':
        c.execute(f'{sql} idx_logs_checksum ON logs (checksum)')
        c.execute(f'{sql} idx_logs_filename ON logs (filename)')
        c.execute(f'{sql} idx_logs_checksum_filename ON logs (checksum, filename)')  # Composite
    else:
        c.execute(f'{sql} idx_sys_checksum ON sys (checksum)')
        c.execute(f'{sql} idx_sys_filename ON sys (filename)')
        c.execute(f'{sql} idx_sys_checksum_filename ON sys (checksum, filename)')


def create_db(database, action=None):
    print('Initializing database...')

    conn = sqlite3.connect(database)
    c = conn.cursor()

    create_table(c, 'logs', ('timestamp', 'filename', 'changetime'), ['hardlinks INTEGER',])

    create_table(c, 'sys', ('timestamp', 'filename', 'changetime',), ['count INTEGER',])

    c.execute('''
    CREATE TABLE IF NOT EXISTS stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        timestamp TEXT,
        filename TEXT,
        changetime TEXT,
        UNIQUE(timestamp, filename, changetime)
        )
    ''')
    conn.commit()
    if action:
        return conn
    else:
        conn.close()


def insert(log, conn, c, table, last_column):  # Log, sys
    global count
    count = getcount(c)

    columns = [
        'timestamp', 'filename', 'changetime', 'inode', 'accesstime',
        'checksum', 'filesize', 'symlink', 'owner', '`group`',
        'permissions', 'casmod', 'lastmodified', last_column
    ]
    placeholders = ', '.join(['?'] * len(columns))
    col_str = ', '.join(columns)
    c.executemany(
        f'INSERT OR IGNORE INTO {table} ({col_str}) VALUES ({placeholders})',
        log
    )

    if table == 'logs':
        blank_row = tuple([None] * len(columns))
        c.execute(
                f'INSERT INTO {table} ({col_str}) VALUES ({", ".join(["?"]*len(columns))})',
                blank_row
        )

    conn.commit()


def insert_if_not_exists(action, timestamp, filename, changetime, conn, c):  # Stats
    timestamp = timestamp or None
    c.execute('''
    INSERT OR IGNORE INTO stats (action, timestamp, filename, changetime)
    VALUES (?, ?, ?, ?)
    ''', (action, timestamp, filename, changetime))
    conn.commit()


def main(dbtarget, xdata, COMPLETE, logging_values, rout, scr, cerr, mMODE, checksum, cdiag, email, ANALYTICSECT, ps, compLVL, user, dcr=False):

    parsedsys = []

    outfile = getnm(dbtarget, '.db')
    sys_table = "sys"

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
    # dbopt = getnm(dbtarget, 'db')   # generic output database
    # with tempfile.TemporaryDirectory(dir='/tmp') as tempdir:
    #     dbopt = os.path.join(tempdir, dbopt)

    app_dir = os.path.dirname(dbtarget)
    dbopt = os.path.join(app_dir, outfile)

    if os.path.isfile(dbtarget):
        sts = decr(dbtarget, dbopt)
        if not sts:
            print('Find out why db not decrypting or delete it to make a new one')
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

                create_table(c, sys_table, ('timestamp', 'filename', 'changetime',), ['count INTEGER',])
                new_profile = True

                try:

                    parsedsys = sysprofile.main(mMODE, logging_values)  # hash base xzms

                except Exception as e:
                    print(f'sysprofile.py failed to hash. {type(e).__name__} {e} \n {traceback.format_exc()} ')
                    parsedsys = None

                if parsedsys:
                    try:

                        insert(parsedsys, conn, c, sys_table, "count")
                        is_ps = True

                    except Exception as e:
                        print(f'sys db failed insert {e}  {type(e).__name__} \n{traceback.format_exc()}')
                        db_error = True

            elif ps:
                print('Sys profile requires the setting checksum to index')

        # Log
        if xdata:

            if goahead:  # Hybrid analysis. Skip first pass ect.

                try:

                    hanly_parallel(rout, scr, cerr, mMODE, xdata, checksum, cdiag, dbopt, is_ps, user, logging_values)

                except Exception as e:
                    print(f"hanlydb failed to process on mode {mMODE}: {e} {traceback.format_exc()}", file=sys.stderr)

                if mMODE == 'mc':
                    x = os.cpu_count()
                    if x:
                        if os.path.isfile(cerr):
                            with open(cerr, 'r') as f:
                                contents = f.read()
                            if not contents:
                                print("No output in cerr", cerr)
                            elif ('Suspect' in contents or 'COLLISION' in contents):
                                print("Warning:  Suspect or collision detected")
                            else:
                                print(f'Detected {x} CPU cores.')
                        else:
                            print(f'Detected {x} CPU cores.')
                if ANALYTICSECT:
                    cprint.green('Hybrid analysis on')

            try:

                parsed = []
                for record in xdata:
                    parsed.append(record[:14])

                insert(parsed, conn, c, "logs", "hardlinks")
                if count % 10 == 0:
                    print(f'{count + 1} searches in gpg database')

            except Exception as e:
                print(f'log db failed insert err: {e} {type(e).__name__}  \n{traceback.format_exc()}')
                db_error = True

            # Check for hash collisions
            if checksum and cdiag:
                ccheck(xdata, cerr, c, ps)

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

            nc = intst(dbopt, compLVL)
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
