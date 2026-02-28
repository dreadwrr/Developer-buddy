#!/usr/bin/env python3
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import tkinter as tk
import traceback
from tkinter import ttk
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from configfunctions import find_install
from configfunctions import get_config
from configfunctions import load_toml
from configfunctions import update_toml_setting
from gpgcrypto import decr
from gpgcrypto import encr
from gpgcrypto import gpg_can_decrypt
from gpgkeymanagement import delete_gpg_keys
from logs import setup_logger
from pyfunctions import get_delete_patterns
from pyfunctions import is_integer
from pyfunctions import reset_csvliteral
from pysql import insert
from pysql import table_has_data
from rntchangesfunctions import cprint
from rntchangesfunctions import name_of
from rntchangesfunctions import cnc

# 02/26/2026

# see pyfunctions.py cache clear patterns for db

# Globals
sort_directions = {}


def redraw_table(table, cur, table_name):

    for row in table.get_children():
        table.delete(row)

    cur.execute(f"SELECT * FROM {table_name}")
    rows = cur.fetchall()

    column_widths = {
        "filename": 900,
        "id": 60,
        "timestamp": 150,
        "accesstime": 150,
        "changetime": 150,
        "inode": 70,
        "filesize": 70,
        "checksum": 270,
        "owner": 65,
        "group": 65,
        "casmod": 65,
        "lastmodified": 150,
        "hardlinks": 65,
        "symlink": 65,
        "permissions": 65,
        "target": 135,
        "mtime_us": 135
    }
    # table["columns"] = [f"Col{i}" for i in range(len(cur.description))]
    # for i, col in enumerate(table["columns"]):
    #     table.heading(col, text=cur.description[i][0])
    #     table.column(col, width=100)

    all_columns = [desc[0] for desc in cur.description]
    column_names = [col for col in all_columns]  # if col != "escapedpath"
    table["columns"] = column_names

    for col in column_names:
        table.heading(col, text=col)

        table.column(col, width=column_widths.get(col, 120), anchor="w", stretch=True)

    table.delete(*table.get_children())

    for col in column_names:
        table.heading(col, text=col, command=lambda _col=col: sort_column(table, _col, column_names))
        table.column(col, width=column_widths.get(col, 120), anchor="w", stretch=True)

    for row in rows:
        display_row = [row[i] for i, col in enumerate(all_columns) if col != "escapedpath"]
        table.insert("", "end", values=display_row)


def hardlinks(database, target, conn, cur, user, email, compLVL):
    try:
        is_error = False

        cur.execute("SELECT filename, inode FROM logs WHERE hardlinks is NOT NULL and hardlinks != ''")
        file_rows = cur.fetchall()

        # Prompt to delete previous hardlink data
        cur.execute("SELECT COUNT(*) FROM logs WHERE hardlinks IS NOT NULL AND hardlinks != ''")
        count = cur.fetchone()[0]
        if count > 0:
            user_input = input("Previous 'hardlinks' data has to be cleared. Continue? (y/n): ").strip().lower()
            if user_input == 'y':
                cur.execute("UPDATE logs SET hardlinks = NULL WHERE hardlinks IS NOT NULL AND hardlinks != ''")
                conn.commit()
            else:
                return 0

        cmd = [
            "sudo",
            "find",
            "/",
            "-xdev",
            "-type", "f",
            "-links", "+1",
            "-printf", "%i %n %p\n"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        ret_code = result.returncode
        is_error = False
        if ret_code != 0:
            if ret_code not in (0, 1):
                is_error = True
            for line in result.stderr.splitlines():
                print(line)
            if is_error:
                print(f"find exited with {ret_code}. An error occurred while retrieving hardlinks:")
                return 1
                # if "Transport" not in line:
                #     if not is_error:
                #         is_error = True
                #         print(f"find exited with {result.returncode}. An error occured while retrieving hardlinks:")
                #     print(line)

        # Build filesystem
        fs_inode_map = defaultdict(list)
        for line in result.stdout.splitlines():
            parts = line.strip().split(None, 2)
            if len(parts) != 3:
                continue
            inode_str, count_str, path = parts
            inode = int(inode_str)
            count_val = int(count_str)
            fs_inode_map[inode].append((count_val, path))

        if not fs_inode_map or not file_rows:
            print("No results nothing to set")
            return True

        db_inode_map = defaultdict(set)
        for filename, inode in file_rows:
            if not filename:
                continue
            if os.path.isfile(filename):
                db_inode_map[int(inode)].add(filename)

        matches = []
        for inode, db_paths in db_inode_map.items():
            if inode in fs_inode_map:
                for path in db_paths:
                    for count_val, fs_path in fs_inode_map[inode]:
                        if path == fs_path:
                            matches.append((count_val, inode, path))
            else:
                for path in db_paths:
                    matches.append((1, inode, path))

        if matches:
            cur.execute("UPDATE logs SET hardlinks = NULL WHERE hardlinks IS NOT NULL AND hardlinks != ''")
            cur.executemany(
                "UPDATE logs SET hardlinks = ? WHERE inode = ? AND filename = ?",
                matches
            )
            conn.commit()
            nc = cnc(target, compLVL)
            rlt = encr(database, target, email, no_compression=nc, dcr=True)
            if rlt:
                print("Hard links updated.")
            else:
                print("Reencryption failed, hardlinks not set.")

    except sqlite3.Error as e:
        print(f"hardlinks Error executing database query/update. err: {type(e).__name__}: {e}")
        conn.rollback()
    except Exception as e:
        import traceback
        print(f"Error setting hardlinks: {e} {type(e).__name__} \n{traceback.format_exc()}")


def clear_cache(database, target, flth, conn, cur, email, usr, compLVL):
    files_d = get_delete_patterns(usr)
    filename_pattern = None
    try:
        for filename_pattern in files_d:
            cur.execute("DELETE FROM logs WHERE filename LIKE ?", (filename_pattern,))
            conn.commit()
            cur.execute("DELETE FROM stats WHERE filename LIKE ?", (filename_pattern,))
            conn.commit()

        nc = cnc(target, compLVL)
        rlt = encr(database, target, email, no_compression=nc, dcr=True)
        if rlt:
            print("Cache files cleared.")
            try:
                reset_csvliteral(flth)
            except Exception as e:
                print(f'Failed to clear csv: {flth} {e} {type(e).__name__} \n{traceback.format_exc()}')

        else:
            print("Reencryption failed cache not cleared.:")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Cache clear failed to write to db. on {filename_pattern if filename_pattern else ''} {e} {type(e).__name__}")


def clear_sys(database, target, conn, cur, config_file, email, compLVL, dcr=True):
    try:
        if table_has_data(conn, "sys"):
            cur.execute("DELETE FROM sys")
            try:
                cur.execute("DELETE FROM sqlite_sequence WHERE name=?", ("sys",))
            except sqlite3.OperationalError:
                pass
            conn.commit()

            nc = cnc(database, compLVL)
            rlt = encr(database, target, email, no_compression=nc, dcr=True)
            if rlt:

                update_toml_setting('shield', 'proteusSHIELD', False, config_file)

                print("Sys table cleared.")
                return True
            else:
                print("Reencryption failed sys not cleared.:")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Sys clear failed to write to db clear fail {type(e).__name__}: {e}")
        logging.error(f"Error clearing sys {e} {type(e).__name__} \n", exc_info=True)
    return False


def activateps(parsedsys, database, target, conn, cur, email, compLVL):
    try:
        insert(parsedsys, conn, cur, "sys", ['count', 'mtime_us'])
        nc = cnc(database, compLVL)
        rlt = encr(database, target, email, no_compression=nc, dcr=True)
        if rlt:
            print("Proteus shield activated.")
        else:
            print("Reencryption failed ps failed.")
            return False
    except Exception as e:
        print('sys db failed insert', e)
        return False
    return True


def run_sys_profile(appdata_local, tempdir, database, target, config_file, log_file, user, email, ll_level, turbo, compLVL):

    script_file = "hash_profile.py"
    script_path = appdata_local / script_file

    try:
        cmd = [
            "sudo",
            sys.executable,
            "-u",
            str(script_path),
            str(appdata_local),
            str(tempdir),
            database,
            target,
            config_file,
            str(log_file),
            email,
            ll_level,
            turbo,
            str(compLVL)
        ]
        script_dir = str(script_path.parent)
        result = subprocess.Popen(cmd, cwd=script_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        stdout = result.stdout
        if stdout is None:
            print("stdout is None")
            return False
            # raise RuntimeError("stdout is None")
        for line in stdout:
            print(line, end="")

        return_code = result.wait()

        if return_code == 0:
            return True

        if result.returncode == 1:
            print("Profile failed in", script_path)
        else:
            print("see logfile ", log_file)
        return False

    except Exception as e:
        msg = f"Error calling {script_path} error: {e} {type(e).__name__}"
        print(msg)
        logging.error(msg, exc_info=True)
    return False


def ps(database, target, conn, cur, config_file, user, email, turbo, compLVL, logging_values):

    log_file = logging_values[0]
    ll_level = logging_values[1]
    appdata_local = logging_values[2]
    tempdir = logging_values[3]

    if not table_has_data(conn, "sys"):

        result = run_sys_profile(appdata_local, tempdir, database, target, config_file, log_file, user, email, ll_level, turbo, compLVL)

    else:

        user_input = input("Previous sys data has to be cleared. continue? (y/n): ").strip().lower()
        if user_input != 'y':
            return False
        print("Clearing sys table")

        if not clear_sys(database, target, conn, cur, config_file, email, compLVL, True):
            print("initial Sys clear failed. exiting...")
            return False

        result = run_sys_profile(appdata_local, tempdir, database, target, config_file, log_file, user, email, ll_level, turbo, compLVL)

    return result


def dexec(cur, actname, limit):
    query = '''
    SELECT *
    FROM stats
    WHERE action = ?
    ORDER BY timestamp DESC
    LIMIT ?
    '''
    cur.execute(query, (actname, limit))
    return cur.fetchall()


def sort_column(tree, col, columns):
    global sort_directions
    # index_ = columns.index(col)
    ascending = sort_directions.get(col, True)
    sort_directions[col] = not ascending
    data = [(tree.set(child, col), child) for child in tree.get_children('')]

    def convert(value):
        if col == "filesize":
            try:
                return int(value)
            except (ValueError, TypeError):
                return -1
        else:
            return value.lower() if isinstance(value, str) else value
    data.sort(key=lambda t: convert(t[0]), reverse=not ascending)
    for index_, (val, item) in enumerate(data):
        tree.move(item, '', index_)


def results(database, target, conn, cur, email, user, flth, config_path, turbo, compLVL, logging_values):
    root = tk.Tk()
    root.title("Database Viewer")
    toolbar = tk.Frame(root)
    toolbar.pack(side=tk.TOP, fill=tk.X)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [t[0] for t in cur.fetchall()] or ["(no tables)"]
    selected_table = tk.StringVar(value=tables[0])

    def clear_sys_and_redraw():
        if clear_sys(database, target, conn, cur, config_path, email, compLVL, dcr=True):
            selected_table.set("logs")
            table_menu.event_generate("<<ComboboxSelected>>")

    def index_system():
        if ps(database, target, conn, cur, config_path, user, email, turbo, compLVL, logging_values):
            selected_table.set("sys")
            table_menu.event_generate("<<ComboboxSelected>>")

    lower_frame = tk.Frame(root)
    lower_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

    table_menu = ttk.Combobox(lower_frame, textvariable=selected_table, values=tables, state="readonly", width=14)
    table_menu.pack(side=tk.LEFT, padx=10)

    table_frame = tk.Frame(root)
    table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    tree = ttk.Treeview(table_frame, show='headings')

    reload_button = tk.Button(
        lower_frame,
        text="",
        width=6,  # small button
        command=lambda: redraw_table(tree, cur, selected_table.get())  # reload the sys table
    )
    reload_button.pack(side=tk.LEFT, padx=(2))
    img_path = os.path.join(logging_values[2], "Documents", "crests", "port.png")
    img = tk.PhotoImage(file=img_path)
    # img = img.subsample(2, 2)
    label = tk.Label(toolbar, image=img)
    label.image = img  # type: ignore
    label.pack(side=tk.LEFT)

    hardlink_button = tk.Button(toolbar, text="Set Hardlinks", command=lambda: hardlinks(database, target, conn, cur, user, email, compLVL))
    hardlink_button.pack(side=tk.RIGHT, padx=10)
    clear_cache_button = tk.Button(toolbar, text="Clear Cache", command=lambda: clear_cache(database, target, flth, conn, cur, email, user, compLVL))
    clear_cache_button.pack(side=tk.RIGHT, padx=10)
    new_button = tk.Button(lower_frame, text="Clear sys", command=lambda: clear_sys_and_redraw())
    new_button.pack(side=tk.RIGHT, padx=10)
    ps_button = tk.Button(lower_frame, text="Proteus Shield", command=lambda: index_system())
    ps_button.pack(side=tk.RIGHT, padx=10)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
    vsb.grid(row=0, column=1, sticky="ns")
    hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=tree.xview)
    hsb.grid(row=1, column=0, sticky="ew")
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    def load_table(table_name: str):
        if table_name == "(no tables)":
            for iid in tree.get_children():
                tree.delete(iid)
            tree["columns"] = ()
            return
        c = conn.cursor()
        c.execute(f"SELECT * FROM \"{table_name}\"")
        rows = c.fetchall()
        columns = [d[0] for d in c.description if d[0] != "escapedpath"]  # columns = [d[0] for d in c.description]
        tree.delete(*tree.get_children())
        tree["columns"] = columns

        for col in columns:
            tree.heading(col, text=col, command=lambda _col=col: sort_column(tree, _col, columns))
            if col == "filename":
                tree.column(col, width=1200, anchor="w", stretch=True)
            elif col == "id":
                tree.column(col, width=60, anchor="w", stretch=True)
            elif col in ("timestamp", "accesstime", "changetime"):
                tree.column(col, width=150, anchor="w", stretch=False)
            elif col in ("inode", "filesize"):
                tree.column(col, width=70, anchor="w", stretch=False)
            elif col == "checksum":
                tree.column(col, width=270, anchor="w", stretch=True)
            elif col in ("owner", "group", "casmod", "hardlinks", "symlink"):
                tree.column(col, width=65, anchor="w", stretch=False)
            elif col in ("permissions",):
                tree.column(col, width=65, anchor="w", stretch=False)
            else:
                tree.column(col, width=120, anchor="w", stretch=True)
        for row in rows:
            display_row = [row[i] for i, d in enumerate(c.description) if d[0] != "escapedpath"]
            tree.insert("", tk.END, values=display_row)   # row)
        tree.yview_moveto(0)
        tree.xview_moveto(0)
        table_frame.update_idletasks()

    def on_select(_event):
        load_table(selected_table.get())
    table_menu.bind("<<ComboboxSelected>>", on_select)
    load_table(tables[0])
    root.mainloop()


def blank_count(curs):
    curs.execute('''
        SELECT COUNT(*)
        FROM logs
        WHERE (timestamp IS NULL OR timestamp = '')
        AND (filename IS NULL OR filename = '')
        AND (inode IS NULL OR inode = '')
        AND (accesstime IS NULL OR accesstime = '')
        AND (checksum IS NULL OR checksum = '')
        AND (filesize IS NULL OR filesize = '')
    ''')
    count = curs.fetchone()
    return count[0]


def averagetm(conn, cur):
    c = conn.cursor()
    c.execute('''
    SELECT timestamp
    FROM logs
    ORDER BY timestamp ASC
    ''')
    timestamps = c.fetchall()
    total_minutes = 0
    valid_timestamps = 0
    for timestamp in timestamps:
        if timestamp and timestamp[0]:
            current_time = datetime.strptime(timestamp[0], "%Y-%m-%d %H:%M:%S")
            total_minutes += current_time.hour * 60 + current_time.minute
            valid_timestamps += 1
    if valid_timestamps > 0:
        avg_minutes = total_minutes / valid_timestamps
        avg_hours = int(avg_minutes // 60)
        avg_minutes = int(avg_minutes % 60)
        avg_time = f"{avg_hours:02d}:{avg_minutes:02d}"
        return avg_time


def showdb(question):
    while True:
        user_input = input(f"{question} (Y/N): ").strip().lower()
        if user_input == 'y':
            return True
        elif user_input == 'n':
            return False
        else:
            print("Invalid input, please enter 'Y' or 'N'.")


def main(usr, reset=None):

    appdata_local = find_install()
    toml_file, _, _, _, _ = get_config(appdata_local, usr)
    config = load_toml(toml_file)
    email = config['backend']['email']
    compLVL = config['logs']['compLVL']
    flth = appdata_local / "flth.csv"
    dbtarget = appdata_local / "recent.gpg"
    ctimecache = appdata_local / "ctimecache.gpg"
    ll_level = config['logs']['logLEVEL']
    root_log_file = config['logs']['rootLOG']
    log_file = config['logs']['userLOG'] if usr != "root" else root_log_file
    turbo = config['search']['mMODE']
    # checksum = config['diagnostics']['checkSUM']

    log_file = appdata_local / "logs" / log_file
    output = name_of(dbtarget, '.db')

    flth = str(flth)
    dbtarget = str(dbtarget)
    toml_file = str(toml_file)

    # agnostic_check = False
    # no_key = False

    if reset:

        return delete_gpg_keys(usr, email, dbtarget, ctimecache)

    try:

        with tempfile.TemporaryDirectory(dir='/tmp') as tempdir:

            logging_values = (log_file, ll_level, appdata_local, tempdir)
            setup_logger(log_file, ll_level, "QUERY")

            dbopt = os.path.join(tempdir, output)

            if not gpg_can_decrypt(usr, dbtarget):
                return 0

            # can easily break if trying to automate fixing keys. let the user do it if wanted.

            result = decr(dbtarget, dbopt)
            if result:

                if os.path.isfile(dbopt):
                    with sqlite3.connect(dbopt) as conn:
                        cur = conn.cursor()
                        # optionally run database commands
                        # cur.execute("DELETE FROM logs WHERE filename = ?", ('/home/guest/Downloads/Untitled' ,))
                        # conn.commit()
                        atime = averagetm(conn, cur)
                        cprint.cyan("Search breakdown")
                        cur.execute("""
                            SELECT
                            datetime(AVG(strftime('%s', accesstime)), 'unixepoch') AS average_accesstime
                            FROM logs
                            WHERE accesstime IS NOT NULL;
                        """)
                        result = cur.fetchone()
                        average_accesstime = result[0] if result and result[0] is not None else None
                        if average_accesstime:
                            print(f'Average access time: {average_accesstime}')
                        print(f'Avg hour of activity: {atime}')
                        cnt = blank_count(cur)
                        cur.execute('''
                        SELECT filesize
                        FROM logs
                        ''')
                        filesizes = cur.fetchall()
                        total_filesize = 0
                        valid_entries = 0
                        for filesize in filesizes:
                            if filesize and is_integer(filesize[0]):  # Check if filesize is valid (not None or blank)
                                total_filesize += int(filesize[0])
                                valid_entries += 1
                        if valid_entries > 0:
                            avg_filesize = total_filesize / valid_entries
                            avg_filesize_kb = int(avg_filesize / 1024)
                            print(f'Average filesize: {avg_filesize_kb} KB')
                            print()
                        print(f'Searches {cnt}')  # count
                        print()
                        cur.execute('''
                        SELECT filename
                        FROM logs
                        WHERE TRIM(filename) != ''
                        ''')  # Ext
                        filenames = cur.fetchall()
                        extensions = []
                        for entry in filenames:
                            filepath = Path(entry[0])
                            filename = filepath.name
                            if filename.startswith('.') or '.' not in filename:
                                ext = '[no extension]'
                            else:
                                ext = '.' + '.'.join(filename.split('.')[1:])
                            extensions.append(ext)
                        print()
                        directories = [os.path.dirname(filename[0]) for filename in filenames]  # top directories
                        directory_counts = Counter(directories)
                        top_3_directories = directory_counts.most_common(3)
                        cprint.cyan("Top 3 directories")
                        for directory, count in top_3_directories:
                            print(f'{count}: {directory}')
                        print()
                        cur.execute("SELECT filename FROM logs WHERE TRIM(filename) != ''")  # common file 5
                        filenames = [row[0] for row in cur.fetchall()]  # end='' prevents extra newlines
                        filename_counts = Counter(filenames)
                        top_5_filenames = filename_counts.most_common(5)
                        cprint.cyan("Top 5 created")
                        for file, count in top_5_filenames:
                            print(f'{count} {file}')
                        top_5_modified = dexec(cur, 'Modified', 5)
                        filenames = [row[3] for row in top_5_modified]
                        filename_counts = Counter(filenames)
                        top_5_filenames = filename_counts.most_common(5)
                        cprint.cyan("Top 5 modified")
                        for filename, count in top_5_filenames:
                            filename = filename.strip()
                            print(f'{count} {filename}')
                        top_7_deleted = dexec(cur, 'Deleted', 7)
                        filenames = [row[3] for row in top_7_deleted]
                        filename_counts = Counter(filenames)
                        top_7_filenames = filename_counts.most_common(7)
                        cprint.cyan("Top 7 deleted")
                        for filename, count in top_7_filenames:
                            filename = filename.strip()
                            print(f'{count} {filename}')
                        top_7_writen = dexec(cur, 'Overwrite', 7)
                        filenames = [row[3] for row in top_7_writen]
                        filename_counts = Counter(filenames)
                        top_7_filenames = filename_counts.most_common(7)
                        cprint.cyan("Top 7 overwritten")
                        for filename, count in top_7_filenames:
                            filename = filename.strip()
                            print(f'{count} {filename}')
                        top_5_nsf = dexec(cur, 'Nosuchfile', 5)
                        filenames = [row[3] for row in top_5_nsf]
                        filename_counts = Counter(filenames)
                        if filename_counts:
                            top_5_filenames = filename_counts.most_common(5)
                            cprint.cyan("Not actually a file")
                            for filename, count in top_5_filenames:
                                print(f'{count} {filename}')
                        print()
                        cprint.green("Filter hits")
                        with open(flth, 'r') as file:
                            for line in file:
                                print(line, end='')
                        if showdb("display database?"):
                            wish_path = shutil.which("wish")
                            if wish_path:
                                print(f'database in: {tempdir}')
                                results(dbopt, dbtarget, conn, cur, email, usr, flth, toml_file, turbo, compLVL, logging_values)
                                return 0
                            else:
                                print("Install tk to display db.")
                        else:
                            return 0
                else:
                    # no recent.db file permission error abort so sql doesnt make an empty database
                    print("Unable to locate database: ", dbopt)

            # User has no key
            elif result is None:
                ctime_path = ctimecache.name
                print(f"There may be no key for {dbtarget} or {ctime_path} delete it to make a new one. or try recentchanges reset")

            else:

                if os.path.isfile(dbtarget):
                    print('Find out why not decrypting. If unable to fix call: recentchanges reset  . unable to decrypt file: ', dbtarget)

                # else if no recent.gpg there was an exception
                return 1

    except Exception as e:
        print(f"Exception while running query {type(e).__name__}: {e}  \n {traceback.format_exc()}")
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: query.py <user>")
        sys.exit(0)

    sys.exit(main(*sys.argv[1:3]))
