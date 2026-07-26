#!/usr/bin/env python3
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import traceback
from collections import Counter, defaultdict
from datetime import datetime
from math import sin, cos, atan2, pi
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
from pyfunctions import cache_clear_patterns
from pyfunctions import is_integer
from pyfunctions import parse_datetime
from pyfunctions import reset_csvliteral
from pysql import blank_count
from pysql import insert
from pysql import insert_mimes
from pysql import table_has_data
from rntchangesfunctions import cnc
from rntchangesfunctions import cprint
from rntchangesfunctions import name_of
try:
    import tkinter as tk
    TK_AVAILABLE = True

except ImportError:
    TK_AVAILABLE = False
try:
    import sv_ttk
    SV_TTK = True

except ImportError:
    SV_TTK = False
try:
    import ttkbootstrap as ttk
    USE_BOOTSTRAP = True

except ImportError:
    from tkinter import ttk
    USE_BOOTSTRAP = False
# 07/25/2026

# see pyfunctions.py cache clear patterns for db


# Globals
BOOTSTRAP_DEFAULT = "darkly"    # default theme for ttkbootstrap
DEFAULT_THEME = "dark"          # light # default for sv azure
LARGE_TABLE_THRESHOLD = 20000   # when to use pagination
sort_directions = {}
TABLE_ROW_COUNTS = {}
after_id = None
COLUMN_WIDTHS = {
    "id": 60,
    "timestamp": 145,
    "filename": 900,
    "changetime": 145,
    "inode": 70,
    "accesstime": 145,
    "checksum": 270,
    "entropy": 65,
    "mime_id": 65,
    "filesize": 70,
    "symlink": 65,
    "owner": 65,
    "group": 65,
    "casmod": 65,
    "target": 65,
    "lastmodified": 145,
    "hardlinks": 65,
    "count": 65,
    "permissions": 120
}
NUMERIC_COLUMNS = {"inode", "filesize", "mime_id", "permissions", "hardlinks", "count"}
REAL_COLUMNS = {"entropy"}


def sort_column(tree, cur, selected_table, _col, column_names):

    if TABLE_ROW_COUNTS.get(selected_table, 0) > LARGE_TABLE_THRESHOLD:
        global sort_directions
        ascending = sort_directions.get(_col, True)
        sort_directions[_col] = not ascending
        sql = f'SELECT * FROM "{selected_table}" ORDER BY "{_col}" {"ASC" if ascending else "DESC"}'

        load_table(tree, cur, sql, selected_table)
    else:
        _sort_column(tree, _col, column_names)


def _sort_column(tree, col, columns):
    global sort_directions
    # index_ = columns.index(col)
    ascending = sort_directions.get(col, True)
    sort_directions[col] = not ascending
    data = [(tree.set(child, col), child) for child in tree.get_children('')]

    def convert(value):
        if col in NUMERIC_COLUMNS:
            try:
                return int(value)
            except (ValueError, TypeError):
                return -1
        elif col in REAL_COLUMNS:
            try:
                return float(value)
            except (ValueError, TypeError):
                return -1.0
        return value.casefold() if isinstance(value, str) else value  # value.lower()

    data.sort(key=lambda t: convert(t[0]), reverse=not ascending)
    for index_, (val, item) in enumerate(data):
        tree.move(item, '', index_)


def insert_batch(table, cur, all_columns, batch_size=500):
    global after_id

    rows = cur.fetchmany(batch_size)

    if not rows:
        after_id = None
        table.yview_moveto(0)
        table.xview_moveto(0)
        table.update_idletasks()
        return

    for row in rows:
        display_row = [
            row[i]
            for i, col in enumerate(all_columns)
            if col != "escapedpath"
        ]
        table.insert("", "end", values=display_row)

    after_id = table.after(10, lambda: insert_batch(table, cur, all_columns))


def load_table(table, cur, sql, table_name, batch_size=500):

    global after_id
    global TABLE_ROW_COUNTS

    if after_id is not None:
        table.after_cancel(after_id)
        after_id = None

    if table_name == "(no tables)":
        table.delete(*table.get_children())
        # for iid in table.get_children():
        #     table.delete(iid)
        table["columns"] = ()
        return

    rows = None

    total_rows = TABLE_ROW_COUNTS.get(table_name, 0)
    if not total_rows:
        cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        total_rows = cur.fetchone()[0]
        TABLE_ROW_COUNTS[table_name] = total_rows

    cur.execute(sql)

    all_columns = [desc[0] for desc in cur.description]
    column_names = [col for col in all_columns if col != "escapedpath"]
    table["columns"] = column_names
    # table["columns"] = [f"Col{i}" for i in range(len(cur.description))]
    # for i, col in enumerate(table["columns"]):
    #     table.heading(col, text=cur.description[i][0])
    #     table.column(col, width=100)

    table.delete(*table.get_children())
    # for row in table.get_children():
    #     table.delete(row)

    for col in column_names:
        table.heading(col, text=col, command=lambda _col=col: sort_column(table, cur, table_name, _col, column_names))
        table.column(col, width=COLUMN_WIDTHS.get(col, 120), anchor="w", stretch=False)
        if col == "filename":
            table.column(col, anchor="w", stretch=True)

    if total_rows > LARGE_TABLE_THRESHOLD:
        insert_batch(table, cur, all_columns, batch_size)
    else:
        rows = cur.fetchall()
        for row in rows:
            display_row = [row[i] for i, col in enumerate(all_columns) if col != "escapedpath"]
            table.insert("", "end", values=display_row)
            # table.insert("", tk.END, values=display_row)   # row)  # orig
        TABLE_ROW_COUNTS[table_name] = len(rows)


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
            rlt = encr(database, target, email, user=user, no_compression=nc, dcr=True)
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


def clear_cache(database, target, flth, conn, cur, email, user, compLVL, cachermPATTERNS):
    files_d = cachermPATTERNS
    filename_pattern = None
    try:
        for filename_pattern in files_d:
            cur.execute("DELETE FROM logs WHERE filename LIKE ?", (filename_pattern,))
            cur.execute("DELETE FROM stats WHERE filename LIKE ?", (filename_pattern,))
        if filename_pattern is not None:
            conn.commit()

        nc = cnc(target, compLVL)
        rlt = encr(database, target, email, user=user, no_compression=nc, dcr=True)
        if rlt:
            print("Cache cleared")
            try:
                is_diff = reset_csvliteral(flth)
                if is_diff:
                    print("Filter hits cleared.")
                x = blank_count(cur)
                if x % 5 == 0:

                    print("for resetting filter hits see filter.py")

            except Exception as e:
                print(f'Failed to clear csv: {flth} {e} {type(e).__name__} \n{traceback.format_exc()}')

        else:
            print("Reencryption failed cache not cleared.:")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Cache clear failed to write to db. on {filename_pattern if filename_pattern else ''} {e} {type(e).__name__}")


def clear_sys(database, target, conn, cur, config_file, email, user, compLVL, dcr=True):
    try:
        if table_has_data(conn, "sys"):
            cur.execute("DELETE FROM sys")
            try:
                cur.execute("DELETE FROM sqlite_sequence WHERE name=?", ("sys",))
            except sqlite3.OperationalError:
                pass
            conn.commit()

            nc = cnc(database, compLVL)
            rlt = encr(database, target, email, user=user, no_compression=nc, dcr=True)
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


def activateps(parsedsys, new_mime_rows, database, target, conn, cur, email, user, compLVL):
    try:
        insert(parsedsys, conn, cur, "sys", ['count', 'mtime_us'])

        insert_mimes(cur, new_mime_rows)
        conn.commit()
        nc = cnc(database, compLVL)
        rlt = encr(database, target, email, user=user, no_compression=nc, dcr=True)
        if rlt:
            print("Proteus shield activated.")
        else:
            print("Reencryption failed ps failed.")
            return False
    except Exception as e:
        print('sys db failed insert', e)
        return False
    return True


def run_sys_profile(appdata_local, tempdir, database, target, config_file, log_file, user, email, ll_level, turbo, compLVL, checkMETHOD):

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
            user,
            ll_level,
            turbo,
            str(compLVL),
            checkMETHOD
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


def ps(database, target, conn, cur, config_file, user, email, turbo, compLVL, checkMETHOD, logging_values):

    log_file = logging_values[0]
    ll_level = logging_values[1]
    appdata_local = logging_values[2]
    tempdir = logging_values[3]

    if not table_has_data(conn, "sys"):

        result = run_sys_profile(appdata_local, tempdir, database, target, config_file, log_file, user, email, ll_level, turbo, compLVL, checkMETHOD)

    else:

        user_input = input("Previous sys data has to be cleared. continue? (y/n): ").strip().lower()
        if user_input != 'y':
            return False
        print("Clearing sys table")

        if not clear_sys(database, target, conn, cur, config_file, email, user, compLVL, True):
            print("initial Sys clear failed. exiting...")
            return False

        result = run_sys_profile(appdata_local, tempdir, database, target, config_file, log_file, user, email, ll_level, turbo, compLVL, checkMETHOD)

    return result


def make_button(parent, text, command, bootstyle="secondary", **kwargs):
    if USE_BOOTSTRAP:
        return ttk.Button(parent, text=text, command=command, bootstyle=bootstyle, **kwargs)
    return tk.Button(parent, text=text, command=command, **kwargs)


def make_combobox(parent, textvariable, values, bootstyle="primary", **kwargs):
    if USE_BOOTSTRAP:
        return ttk.Combobox(parent, textvariable=textvariable, values=values, bootstyle=bootstyle, **kwargs)
    return ttk.Combobox(parent, textvariable=textvariable, values=values, **kwargs)


def results(database, target, conn, cur, email, user, flth, config_path, turbo, compLVL, checkMETHOD, bootstrapTHEME, defaultTHEME, logging_values, cachermPATTERNS):

    # for testing theme precedence
    # global USE_BOOTSTRAP
    # USE_BOOTSTRAP = False

    img_path = os.path.join(logging_values[2], "Documents", "crests", "port.png")
    icon_path = img_path

    if USE_BOOTSTRAP:
        root = ttk.App(title="Database Viewer", iconphoto=icon_path)  # , theme=bootstrapTHEME
        img = tk.PhotoImage(file=icon_path)
    else:
        azure_path = os.path.join(logging_values[2], "azure.tcl")
        forest_dark = os.path.join(logging_values[2], "forest-dark.tcl")
        forest_light = os.path.join(logging_values[2], "forest-light.tcl")

        if defaultTHEME not in ("dark", "light"):
            defaultTHEME = "dark"

    root = tk.Tk()
    root.title("Database Viewer")
    img = tk.PhotoImage(file=icon_path)
    root.iconphoto(True, img)
    if SV_TTK:
        sv_ttk.set_theme(defaultTHEME)
    elif os.path.isfile(azure_path):
        root.tk.call("source", azure_path)
        root.tk.call("set_theme", defaultTHEME)
    elif os.path.isfile(forest_dark) and defaultTHEME == "dark":
        root.tk.call("source", forest_dark)
        ttk.Style().theme_use("forest-dark")
    elif os.path.isfile(forest_light) and defaultTHEME == "light":
        root.tk.call("source", forest_light)
        ttk.Style().theme_use("forest-light")

    toolbar = ttk.Frame(root)
    toolbar.pack(side=tk.TOP, fill=tk.X)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [t[0] for t in cur.fetchall() if "analytics" not in t[0]] or ["(no tables)"]
    selected_table = tk.StringVar(value=tables[0])

    def clear_sys_and_redraw():
        if clear_sys(database, target, conn, cur, config_path, email, user, compLVL, dcr=True):
            selected_table.set("logs")
            table_menu.event_generate("<<ComboboxSelected>>")

    def index_system():
        if ps(database, target, conn, cur, config_path, user, email, turbo, compLVL, checkMETHOD, logging_values):
            selected_table.set("sys")
            table_menu.event_generate("<<ComboboxSelected>>")

    lower_frame = ttk.Frame(root)
    lower_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

    table_menu = make_combobox(lower_frame, selected_table, tables, state="readonly", width=14)
    table_menu.pack(side=tk.LEFT, padx=10)

    table_frame = ttk.Frame(root)
    table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    tree = ttk.Treeview(table_frame, show='headings')

    reload_button = make_button(lower_frame, "", lambda: load_table(tree, cur, f'SELECT * FROM "{selected_table.get()}"', selected_table.get()), bootstyle="secondary", width=6)

    reload_button.pack(side=tk.LEFT, padx=(2))

    if USE_BOOTSTRAP:

        if bootstrapTHEME not in root.theme_names():
            bootstrapTHEME = BOOTSTRAP_DEFAULT

        theme_var = tk.StringVar(value=bootstrapTHEME)
        theme_menu = ttk.Combobox(
            lower_frame,
            textvariable=theme_var,
            values=root.theme_names(),
            state="readonly",
            width=12,
        )
        theme_menu.pack(side=tk.LEFT, padx=10)
        theme_menu.bind("<<ComboboxSelected>>", lambda e: root.theme_use(theme_var.get()))
        root.theme_use(bootstrapTHEME)

    label = ttk.Label(toolbar, image=img)  # img = img.subsample(2, 2)

    label.image = img
    label.pack(side=tk.LEFT)

    hardlink_button = make_button(toolbar, "Set Hardlinks", lambda: hardlinks(database, target, conn, cur, email, compLVL), bootstyle="primary")
    hardlink_button.pack(side=tk.RIGHT, padx=10)
    clear_cache_button = make_button(toolbar, "Clear Cache", lambda: clear_cache(database, target, flth, conn, cur, email, user, compLVL, cachermPATTERNS), bootstyle="primary")
    clear_cache_button.pack(side=tk.RIGHT, padx=10)
    new_button = make_button(lower_frame, "Clear sys", lambda: clear_sys_and_redraw(), bootstyle="primary")
    new_button.pack(side=tk.RIGHT, padx=10)
    ps_button = make_button(lower_frame, "Proteus Shield", lambda: index_system(), bootstyle="primary")
    ps_button.pack(side=tk.RIGHT, padx=10)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
    vsb.grid(row=0, column=1, sticky="ns")
    hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=tree.xview)
    hsb.grid(row=1, column=0, sticky="ew")
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    def on_select(_event):
        load_table(tree, cur, f'SELECT * FROM "{selected_table.get()}"', selected_table.get())
    table_menu.bind("<<ComboboxSelected>>", on_select)
    load_table(tree, cur, f'SELECT * FROM "{tables[0]}"', tables[0])

    tree.yview_moveto(0)
    tree.xview_moveto(0)
    table_frame.update_idletasks()
    root.mainloop()


# ORDER BY timestamp DESC
# LIMIT ?
def dexec(cur, actname, limit):
    query = '''
    SELECT *
    FROM stats
    WHERE action = ?
    '''
    cur.execute(query, (actname,))
    return cur.fetchall()


def average_time(conn, cur):
    # original function for average access time and file activity
    # Would be inaccurate for times that wrap around ie 23:00 - 01:00
    # not in use
    cur.execute('''
    SELECT timestamp
    FROM logs
    ORDER BY timestamp ASC
    ''')
    timestamps = cur.fetchall()
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
    return "N/A"


def clock_average(rows):
    sum_sin = 0
    sum_cos = 0
    n = 0

    for r in rows:
        if not r or not r[0]:
            continue

        # seconds = int(r[0]) % 86400  # time of day only
        dt = datetime.fromtimestamp(int(r[0]))  # local time

        seconds = (
            dt.hour * 3600 +
            dt.minute * 60 +
            dt.second
        )
        angle = 2 * pi * seconds / 86400

        sum_sin += sin(angle)
        sum_cos += cos(angle)
        n += 1

    if n == 0:
        return "N/A"

    angle = atan2(sum_sin, sum_cos)
    if angle < 0:
        angle += 2 * pi

    avg_seconds = angle * 86400 / (2 * pi)

    hours = int(avg_seconds // 3600)
    minutes = int((avg_seconds % 3600) // 60)

    return f"{hours:02d}:{minutes:02d}"


def search_times(cur):
    groups, current = [], []

    # keep order exactly as in database with id column sort
    cur.execute("""
        SELECT timestamp
        FROM logs
        ORDER BY id
    """)
    rows = cur.fetchall()

    for row in rows:
        ts = row[0]

        is_blank = (ts is None or ts == "")

        if is_blank:
            if current:
                groups.append(current)
                current = []
            continue

        dt = parse_datetime(ts)
        if dt:
            current.append([dt.timestamp(),])

    if current:
        groups.append(current)

    # first timestamp or start of each search
    first_times = [group[0] for group in groups if group]

    return first_times


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
    toml_file, home_dir, _, _, uid, gid = get_config(appdata_local, usr)

    config = load_toml(toml_file)
    cachermPATTERNS = config['backend']['cachermPATTERNS']
    cachermPATTERNS = cache_clear_patterns(usr, cachermPATTERNS)
    email = config['backend']['email']
    bootstrapTHEME = config['display']['bootstrapTHEME']
    defaultTHEME = config['display']['defaultTHEME']
    compLVL = config['logs']['compLVL']
    ll_level = config['logs']['logLEVEL']
    root_log_file = config['logs']['rootLOG']
    log_file = config['logs']['userLOG'] if usr != "root" else root_log_file
    turbo = config['search']['mMODE']
    # checksum = config['diagnostics']['checkSUM']
    checkMETHOD = config['diagnostics']['checkMETHOD']
    pst_data = Path(home_dir) / ".local" / "share" / "save-changesnew"
    flth = pst_data / "flth.csv"
    dbtarget = pst_data / "recent.gpg"
    ctimecache = pst_data / "ctimecache.gpg"
    log_file = appdata_local / "logs" / log_file

    output = name_of(dbtarget, '.db')

    flth = str(flth)
    dbtarget = str(dbtarget)
    toml_file = str(toml_file)

    # agnostic_check = False
    # no_key = False

    if reset:

        return delete_gpg_keys(usr, email, dbtarget, ctimecache, flth)

    try:
        # with tempfile.TemporaryDirectory() as tempdir:
        with tempfile.TemporaryDirectory(dir='/tmp') as tempdir:

            logging_values = (log_file, ll_level, appdata_local, tempdir)
            setup_logger(log_file, ll_level, "QUERY")

            dbopt = os.path.join(tempdir, output)
            # dbopt = os.path.join(dst, output)
            if not gpg_can_decrypt(usr, dbtarget):
                return 0

            # can easily break if trying to automate fixing keys. let the user do it if wanted.

            result, error_msg = decr(dbtarget, dbopt, usr)
            if result:

                # change_perm(dbopt, uid, gid)
                # subprocess.run(["sudo", "chown", "guest:guest", dbopt], check=True)
                if os.path.isfile(dbopt):
                    with sqlite3.connect(dbopt) as conn:
                        cur = conn.cursor()
                        # optionally run database commands
                        # cur.execute("DELETE FROM logs WHERE filename = ?", ('/home/guest/Downloads/Untitled' ,))
                        # conn.commit()

                        cprint.cyan("Search breakdown")

                        # average file access time
                        cur.execute("""
                            SELECT strftime('%s', accesstime)
                            FROM logs
                            WHERE accesstime IS NOT NULL;
                        """)
                        rows = cur.fetchall()
                        avg_atime = clock_average(rows)
                        print(f'Average access time: {avg_atime}')

                        # average time of user searches
                        rows = search_times(cur)
                        avg_search = clock_average(rows)
                        print(f'Avg hour of activity: {avg_search}')  # atime = average_time(conn, cur) old way which would be incorrect

                        # average file modified time - which is not a valid heuristic
                        # cur.execute("SELECT strftime('%s', timestamp) FROM logs")
                        # rows = cur.fetchall()
                        # avg_mtime = clock_average(rows)
                        # log_fn(f'Average time of file activity: {avg_mtime}')
                        # end Search time area
                        cnt = blank_count(cur)
                        cur.execute('''
                        SELECT filesize
                        FROM logs
                        ''')
                        filesizes = cur.fetchall()
                        total_filesize = 0
                        valid_entries = 0
                        for filesize in filesizes:
                            if is_integer(filesize[0]):
                                sze = int(filesize[0])
                                if sze > 0:
                                    total_filesize += sze
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
                        filenames = [row[0] for row in filenames]  # replaces ln 646
                        extensions = []
                        directories = []
                        for filename in filenames:
                            if not filename:
                                continue
                            directories.append(os.path.dirname(filename))  # get the top directories as well
                            filepath = Path(filename)
                            filename = filepath.name
                            if filename.startswith('.') or '.' not in filename:
                                ext = '[no extension]'
                            else:
                                ext = '.' + '.'.join(filename.split('.')[1:])
                            extensions.append(ext)
                        if extensions:
                            counter = Counter(extensions)
                            top_3 = counter.most_common(3)
                            cprint.cyan("Most common extensions")
                            for ext, count in top_3:
                                print(f"{ext}")
                        print()
                        directory_counts = Counter(directories)
                        top_3_directories = directory_counts.most_common(3)
                        cprint.cyan("Top 3 directories")
                        for directory, count in top_3_directories:
                            print(f'{count}: {directory}')
                        print()
                        # cur.execute("SELECT filename FROM logs WHERE TRIM(filename) != ''")  # common file 5 # original
                        # filenames = [row[0] for row in cur.fetchall()]  # end='' prevents extra newlines # original
                        filename_counts = Counter(filenames)
                        top_5_filenames = filename_counts.most_common(5)
                        cprint.cyan("Top 5 created")
                        for file, count in top_5_filenames:
                            print(f'{count} {file}')
                        top_5_modified = dexec(cur, 'Modified', 5)
                        filenames = [row[3] for row in top_5_modified]
                        filename_counts = Counter(filenames)
                        top_5_filenames = filename_counts.most_common(5)
                        cprint.cyan("Most modified")
                        for filename, count in top_5_filenames:
                            filename = filename.strip()
                            print(f'{count} {filename}')
                        top_7_deleted = dexec(cur, 'Deleted', 5)
                        filenames = [row[3] for row in top_7_deleted]
                        filename_counts = Counter(filenames)
                        top_7_filenames = filename_counts.most_common(7)
                        cprint.cyan("Top 5 deleted")
                        for filename, count in top_7_filenames:
                            filename = filename.strip()
                            print(f'{count} {filename}')
                        top_7_writen = dexec(cur, 'Overwrite', 3)
                        filenames = [row[3] for row in top_7_writen]
                        filename_counts = Counter(filenames)
                        top_7_filenames = filename_counts.most_common(7)
                        cprint.cyan("Top 3 overwritten")
                        for filename, count in top_7_filenames:
                            filename = filename.strip()
                            print(f'{count} {filename}')
                        top_5_nsf = dexec(cur, 'Nosuchfile', 5)
                        filenames = [row[3] for row in top_5_nsf]
                        filename_counts = Counter(filenames)
                        if filename_counts:
                            top_5_filenames = filename_counts.most_common(5)
                            cprint.cyan("Top 5 Thats not actually a file")
                            for filename, count in top_5_filenames:
                                print(f'{count} {filename}')
                        print()
                        cprint.green("Filter hits")
                        if os.path.isfile(flth):
                            with open(flth, 'r') as file:
                                for line in file:
                                    print(line, end='')

                        res = showdb("display database?")
                        if res:
                            if TK_AVAILABLE:
                                _display = os.environ.get('DISPLAY')
                                wish_path = shutil.which("wish")
                                if _display and wish_path:
                                    print(f'database in: {tempdir}')

                                    results(dbopt, dbtarget, conn, cur, email, usr, flth, toml_file, turbo, compLVL, checkMETHOD, bootstrapTHEME, defaultTHEME, logging_values, cachermPATTERNS)
                                    return 0
                                elif not wish_path:
                                    print("Install tk to display db.")
                                elif not _display:
                                    print("No X11 display.")
                            else:
                                print("tk not available, skipping database display.")
                        else:
                            return 0
                else:
                    # no recent.db file permission error abort so sql doesnt make an empty database
                    print("Unable to locate database: ", dbopt)

            else:
                print(error_msg)
                if os.path.isfile(dbtarget):
                    ctime_path = ctimecache.name
                    print(f"There may be no key for {dbtarget} or {ctime_path} delete it to make a new one. or try recentchanges reset")

                return 1

    except Exception as e:
        print(f"Exception while running query {type(e).__name__}: {e}  \n {traceback.format_exc()}")
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: query.py <user>")
        sys.exit(0)

    sys.exit(main(*sys.argv[1:3]))
