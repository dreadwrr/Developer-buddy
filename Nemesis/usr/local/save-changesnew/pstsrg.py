#!/usr/bin/env python3
# pstsrg.py - Process and store logs in a SQLite database, encrypting the database       12/23/2025
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import traceback
from hanlyparallel import hanly_parallel
from pyfunctions import ap_decode
from pyfunctions import CYAN, GREEN, RESET
from pyfunctions import ccheck
from pyfunctions import getcount
from pyfunctions import getnm
from pyfunctions import intst
from pyfunctions import removefile
from pyfunctions import to_bool

# Globals
count = 0
QUOTED_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def encr(database, opt, email, no_compression, dcr=False):
    try:
        cmd = [
                "gpg",
                "--yes",
                "--encrypt",
                "-r", email,
                "-o", opt,
        ]
        if no_compression:
            cmd.extend(["--compress-level", "0"])
        cmd.append(database)
        subprocess.run(cmd, check=True)
        if not dcr:
            os.remove(database)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Encryption failed: {e}")
        return False


def decr(src, opt):
    if os.path.isfile(src):
        try:
            cmd = [
                "gpg",
                "--yes",
                "--decrypt",
                "-o", opt,
                src
            ]
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Decryption failed: {e}")
            return False
    else:
        print('no .gpg file')
        return False


def table_exists_and_has_data(conn, table_name):
    c = conn.cursor()
    c.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table_name,))
    if not c.fetchone():
        return False
    c.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
    if c.fetchone():
        return True
    else:
        return False


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


def create_db(database, action=False):
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
        return (conn)
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


def parse_line(line):
    quoted_match = QUOTED_RE.search(line)
    if not quoted_match:
        return None
    raw_filepath = quoted_match.group(1)

    filepath = ap_decode(raw_filepath)

    # Remove quoted path
    line_without_file = line.replace(quoted_match.group(0), '').strip()
    other_fields = line_without_file.split()

    if len(other_fields) < 7:
        return None

    timestamp1 = other_fields[0] + ' ' + other_fields[1]
    timestamp2 = other_fields[2] + ' ' + other_fields[3]
    inode = other_fields[4]
    timestamp3 = other_fields[5] + ' ' + other_fields[6]
    rest = other_fields[7:]

    return [timestamp1, filepath, timestamp2, inode, timestamp3] + rest


def parselog(file, table, checksum):

    results = []

    with open(file, 'r') as file:

        for line in file:
            try:
                inputln = parse_line(line)
                if not inputln or not inputln[1].strip():
                    continue

                n = len(inputln)
                if table == 'sortcomplete':
                    if checksum:
                        if n < 15:
                            print("parselog sortcomplete setting checksum, input out of boundaries skipping")
                            continue
                    else:
                        if n < 10:
                            print("parselog sortcomplete setting no checksum, input out of boundaries skipping")
                            continue

                timestamp = None if inputln[0] in ("None", "") else inputln[0]
                filename = None if inputln[1] in ("", "None") else inputln[1]
                changetime = None if inputln[2] in ("", "None") else inputln[2]
                inode = None if inputln[3] in ("", "None") else inputln[3]
                accesstime = None if inputln[4] in ("", "None") else inputln[4]
                checks = None if n > 5 and inputln[5] in ("", "None") else (inputln[5] if n > 5 else None)
                filesize = None if n > 6 and inputln[6] in ("", "None") else (inputln[6] if n > 6 else None)
                sym = None if n <= 7 or inputln[7] in ("", "None") else inputln[7]
                onr = None if n <= 8 or inputln[8] in ("", "None") else inputln[8]
                gpp = None if n <= 9 or inputln[9] in ("", "None") else inputln[9]
                pmr = None if n <= 10 or inputln[10] in ("", "None") else inputln[10]
                cam = None if n <= 11 or inputln[11] in ("", "None") else inputln[11]
                timestamp1 = None if n <= 12 or inputln[12] in ("", "None") else inputln[12]
                timestamp2 = None if n <= 13 or inputln[13] in ("", "None") else inputln[13]
                lastmodified = None if not timestamp1 or not timestamp2 else f"{timestamp1} {timestamp2}"
                usec = None if n <= 14 or inputln[14] in ("", "None") else inputln[14]
                hardlink_count = None if n <= 15 or inputln[15] in ("", "None") else inputln[15]

                if table == 'sys':
                    count = 0
                    results.append((timestamp, filename, changetime, inode, accesstime, checks, filesize, sym, onr, gpp, pmr, cam, lastmodified, count))
                elif table == 'sortcomplete':

                    if not checksum:
                        cam = checks
                        timestamp1 = filesize
                        timestamp2 = sym
                        lastmodified = None if not timestamp1 or not timestamp2 else f"{timestamp1} {timestamp2}"
                        usec = onr
                        hardlink_count = gpp
                        checks = filesize = sym = onr = gpp = None

                    results.append((timestamp, filename, changetime, inode, accesstime, checks, filesize, sym, onr, gpp, pmr, cam, lastmodified, hardlink_count, usec))
                else:
                    raise ValueError("Supplied table not in accepted boundaries: sys or sortcomplete. value supplied", table)
            except Exception as e:
                print(f'Problem detected in parser parselog for line {line} err: {type(e).__name__}: {e}')

    return results


def statparse(line, outputlist):
    parts = line.strip().split(maxsplit=5)
    if len(parts) < 6:
        return
    action = parts[0]
    date = None if parts[1] == "None" else parts[1]
    time = None if parts[2] == "None" else parts[2]
    cdate = None if parts[3] == "None" else parts[3]
    ctime = None if parts[4] == "None" else parts[4]
    fp = parts[5]
    filename = fp.strip()

    timestamp = None if date is None or time is None else f"{date} {time}"
    changetime = None if cdate is None or ctime is None else f"{cdate} {ctime}"

    if filename:
        outputlist.append((action, timestamp, changetime, filename))


def hash_system_profile(turbo):

    sys_results = []

    print(f'{CYAN}Generating system profile from base .xzms.{RESET}')
    print("Turbo is:", turbo)
    result = subprocess.run(["/usr/local/save-changesnew/sysprofile", turbo], capture_output=True, text=True)
    r = result.returncode

    if r != 0:
        if r == 6:
            print("SORTCOMPLETE was empty.")
        else:
            print("return code:", r)
        print("Bash failed to hash profile.")
    else:
        try:

            sortcomplete_path = result.stdout.strip()

            if os.path.isfile(sortcomplete_path):

                checkSUM = True
                sys_results = parselog(sortcomplete_path, 'sys', checkSUM)   # sys

                sortcomplete_dir = os.path.dirname(sortcomplete_path)

                if os.path.isdir(sortcomplete_dir):
                    if "tmp" in sortcomplete_dir and "_" in sortcomplete_path:
                        shutil.rmtree(sortcomplete_dir)
            else:
                print("hash_system_profile Missing SORTCOMPLETE")

            return sys_results

        except Exception as e:
            print(f"exception hash_system_profile likely parsing error: {e} :{type(e).__name__} \n{traceback.format_exc()}")

    return None


# trying to insert data if anything fails dont encrypt it at the end .
# if hybrid analysis fails it doesnt effect the data
# if only encryption fails leave the db file so it can be manually encrypted with pasted command.
# error codes 2 & 3 are gpg problems. error code 4 is database problem. error code 1 is permissive or general failure
def main():

    xdata = sys.argv[1]   # data source
    COMPLETE = sys.argv[2]   # nsf
    dbtarget = sys.argv[3]   # the target
    rout = sys.argv[4]    # tmp holds action
    checksum = to_bool(sys.argv[5])   # important
    cdiag = to_bool(sys.argv[6])    # setting
    user = sys.argv[7]
    email = sys.argv[8]
    turbo = sys.argv[9]   # mc
    ANALYTICSECT = to_bool(sys.argv[10])
    ps = to_bool(sys.argv[11])   # proteusshield
    compLVL = int(sys.argv[12])

    stats = []
    parsed = []
    parsed_sys = []

    scr = '/tmp/scr'
    cerr = '/tmp/cerr'

    db_error = False
    goahead = True
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

    dbopt = getnm(dbtarget, '.db')
    app_dir = os.path.dirname(dbtarget)
    dbopt = os.path.join(app_dir, dbopt)

    if os.path.isfile(dbtarget):
        sts = decr(dbtarget, dbopt)
        if not sts:
            print('Find out why db not decrypting or delete it to make a new one.')
            return 2
    else:
        try:
            conn = create_db(dbopt, action=True)
            print(f'{GREEN}Persistent database created.{RESET}')
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

        parsed = parselog(xdata, 'sortcomplete', checksum)   # SORTCOMPLETE/Log

        # initial Sys profile
        if ps:
            sys_table = "sys"
            if not table_exists_and_has_data(conn, sys_table) and checksum:

                parsed_sys = hash_system_profile(turbo)

                if parsed_sys:
                    try:

                        insert(parsed_sys, conn, c, sys_table, "count")

                    except Exception as e:
                        print(f'sys db failed insert {e}  {type(e).__name__} \n{traceback.format_exc()}')
                        db_error = True

        # Log
        if parsed:
            if goahead:   # Hybrid analysis. Skip first pass ect.

                try:

                    hanly_parallel(rout, scr, cerr, parsed, checksum, cdiag, dbopt, ps, turbo, user)

                except Exception as e:
                    print(f"hanlydb failed to process on mode {turbo}: {e} {traceback.format_exc()}", file=sys.stderr)

                if turbo == 'mc':
                    x = os.cpu_count()
                    if x:
                        if os.path.isfile(cerr):
                            contents = None
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
                        print(f'{GREEN}Hybrid analysis on{RESET}')
            try:

                xdata = []
                for record in parsed:
                    xdata.append(record[:-1])   # remove the epoch that was used in hanly. it was carried over from bash

                insert(xdata, conn, c, "logs", "hardlinks")
                if count % 10 == 0:
                    print(f'{count + 1} searches in gpg database')

            except Exception as e:
                print(f'log db failed insert err: {e} {type(e).__name__}  \n{traceback.format_exc()}')
                db_error = True

            # Check for hash collisions
            if checksum and cdiag:
                ccheck(xdata, cerr, c, ps)

        # Stats
        if os.path.isfile(rout):

            try:

                with open(rout, 'r', newline='') as record:
                    for line in record:
                        statparse(line, stats)

                if os.path.isfile(COMPLETE) and os.path.getsize(COMPLETE) > 0:
                    with open(COMPLETE, 'r', newline='') as records:
                        for line in records:
                            statparse(line, stats)

                if stats:

                    for record in stats:
                        action = record[0]
                        timestamp = record[1]
                        changetime = record[2]
                        fp = record[3]

                        insert_if_not_exists(action, timestamp, fp, changetime, conn, c)

            except Exception as e:
                print(f'stats db failed to insert err: {e}  \n{traceback.format_exc()}')
                db_error = True

    if not db_error:  # Encrypt if o.k.
        try:

            nc = intst(dbopt, compLVL)
            sts = encr(dbopt, dbtarget, email, no_compression=nc, dcr=True)
            if not sts:
                res = 3  # & 2 gpg problem
                print(f'Failed to encrypt database. Run   gpg --yes -e -r {email} -o {dbtarget} {dbopt}   before running again.')

        except Exception as e:
            res = 3
            print(f'Encryption failed: {e}')

    else:
        res = 4  # delete any changes made.
        print('There is a problem with the database.')

    if res != 3:
        removefile(dbopt)

    return res


if __name__ == "__main__":
    if len(sys.argv) < 13:
        print("pstsrg Not enough arguments. quitting")
        sys.exit(1)
    sys.exit(main())
