#!/userbin/env python3
import os
import pyfunctions
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import ttk
from collections import Counter
from datetime import datetime
from pstsrg import decr
from pstsrg import encr
from pyfunctions import getcount
from pyfunctions import get_delete_patterns
from pyfunctions import is_integer
sort_directions = {}
def hardlinks(database, target, email, conn, cur):
	cur.execute("SELECT COUNT(*) FROM logs WHERE hardlinks IS NOT NULL AND hardlinks != ''")
	count = cur.fetchone()[0]
	if count > 0:
		user_input = input("Previous 'hardlinks' data has to be cleared. continue? (y/n): ").strip().lower()
		if user_input == 'y':
			cur.execute("UPDATE logs SET hardlinks = NULL WHERE hardlinks IS NOT NULL AND hardlinks != ''")
			conn.commit()
		else:
			return 0
	query = """
	UPDATE logs
	SET hardlinks = CASE 
					WHEN (SELECT COUNT(*) 
							FROM logs AS l2 
							WHERE l2.inode = logs.inode 
							AND l2.inode IS NOT NULL
							AND l2.filename != logs.filename) > 0
					THEN (SELECT COUNT(*) 
							FROM logs AS l2 
							WHERE l2.inode = logs.inode 
							AND l2.inode IS NOT NULL
							AND l2.filename != logs.filename)
					ELSE NULL
					END
	WHERE inode IS NOT NULL;
	"""
	try:
		cur.execute(query)
		conn.commit()
		rlt=encr(database, target, email, "False", "False")
		if rlt:
			print("Hard links updated")
		else:
			print(f"Reencryption failed hardlinks not set.")	
	except sqlite3.Error as e:
		print(f"Error executing updating db. data preserved.: {e}")
		conn.rollback()
def clear_cache(database, target, email, usr, dbp, conn, cur):
		files_d = get_delete_patterns(usr, dbp)
		try:
			for filename_pattern in files_d:
				cur.execute("DELETE FROM logs WHERE filename LIKE ?", (filename_pattern,))
				conn.commit()
				cur.execute("DELETE FROM stats WHERE filename LIKE ?", (filename_pattern,))
				conn.commit()
			rlt=encr(database, target, email,"False", "False")
			if rlt:
				print("Cache files cleared.")
				try:
					result=subprocess.run(["/usr/local/save-changesnew/clearcache",  usr, "yes"],check=True,capture_output=True,text=True)
					print(result)
				except subprocess.CalledProcessError as e:
					print("Bash failed to clear flth.csv:", e.returncode)
					print(e.stderr)
			else:
				print(f"Reencryption failed cache not cleared.:")		
		except sqlite3.Error as e:
			conn.rollback()
			print(f"Cache clear failed to write to db. on {filename_pattern}")
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
    index = columns.index(col)
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
def results(database, conn, cur, target, email, user, dbp):
    root = tk.Tk()
    root.title("Database Viewer")
    toolbar = tk.Frame(root)
    toolbar.pack(side=tk.TOP, fill=tk.X)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [t[0] for t in cur.fetchall()] or ["(no tables)"]
    selected_table = tk.StringVar(value=tables[0])
    table_menu = ttk.Combobox(toolbar, textvariable=selected_table, values=tables, state="readonly", width=30)
    table_menu.pack(side=tk.LEFT, padx=10, pady=10)
    # load_btn = tk.Button(toolbar, text="Load Table",
    #                      command=lambda: load_table(selected_table.get()))
    # load_btn.pack(side=tk.LEFT, padx=6, pady=10)
    hardlink_button = tk.Button(toolbar, text="Set Hardlinks",
        command=lambda: hardlinks(database, target, email, conn, cur))
    hardlink_button.pack(side=tk.RIGHT, padx=10, pady=10)
    clear_cache_button = tk.Button(toolbar, text="Clear Cache",
        command=lambda: clear_cache(database, target, email, user, dbp, conn, cur))
    clear_cache_button.pack(side=tk.RIGHT, padx=10, pady=10)
    # Container for Tree + scrollbars (keeps layout stable)
    table_frame = tk.Frame(root)
    table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    tree = ttk.Treeview(table_frame, show='headings')
    tree.grid(row=0, column=0, sticky="nsew")
    vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
    vsb.grid(row=0, column=1, sticky="ns")
    hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=tree.xview)
    hsb.grid(row=1, column=0, sticky="ew")
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)
    def load_table(table_name: str):
        # Bail out if there are no real tables
        if table_name == "(no tables)":
            # Clear tree content safely
            for iid in tree.get_children():
                tree.delete(iid)
            tree["columns"] = ()
            return
        c = conn.cursor()
        c.execute(f"SELECT * FROM \"{table_name}\"")
        rows = c.fetchall()
        columns = [d[0] for d in c.description]
        tree.delete(*tree.get_children())
        # Rebuild columns (don’t recreate widgets; just reconfigure)
        tree["columns"] = columns
        for col in columns:
            tree.heading(col, text=col, command=lambda _col=col: sort_column(tree, _col, columns))
            if col == "filename":
                tree.column(col, width=600, anchor="w", stretch=True)
            elif col in ("timestamp", "accesstime"):
                tree.column(col, width=160, anchor="w", stretch=False)
            elif col == "checksum":
                tree.column(col, width=300, anchor="w", stretch=True)
            elif col in ("owner",):
                tree.column(col, width=90, anchor="w", stretch=False)
            elif col in ("permission",):
                tree.column(col, width=150, anchor="w", stretch=False)
            else:
                tree.column(col, width=120, anchor="w", stretch=True)
        for row in rows:
            tree.insert("", tk.END, values=row)
        tree.yview_moveto(0)
        tree.xview_moveto(0)
        table_frame.update_idletasks()
    def on_select(_event):
        load_table(selected_table.get())
    table_menu.bind("<<ComboboxSelected>>", on_select)
    load_table(tables[0])
    root.mainloop()
def averagetm(conn, cur):
    cur = conn.cursor()
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
        avg_minutes = total_minutes / len(timestamps)
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
def main() :
	dbtarget=sys.argv[1]
	email=sys.argv[2]
	usr=sys.argv[3]
	dbpst=sys.argv[4]
	output = os.path.splitext(os.path.basename(dbtarget))[0]
	with tempfile.TemporaryDirectory(dir='/tmp') as tempdir:
		dbopt=os.path.join(tempdir, output + '.db')
		if decr(dbtarget, dbopt):
				if os.path.isfile(dbopt):
					with sqlite3.connect(dbopt) as conn:
						cur = conn.cursor()
						cur.execute("DELETE FROM logs WHERE filename = ?", ('/home/guest/Downloads/Untitled' ,))
						conn.commit()
						atime=averagetm(conn, cur)
						print(f"{pyfunctions.CYAN}Search breakdown{pyfunctions.RESET}")
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
						cnt = getcount(cur)
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
						print(f'Searches {cnt}') # count
						print()
						cur.execute('''
						SELECT filename
						FROM logs
						WHERE TRIM(filename) != ''
						''') # Ext
						filenames = cur.fetchall()
						extensions = []
						for entry in filenames:
							filepath = entry[0]
							if '.' in filepath:
								ext = '.' + filepath.split('.')[-1] if '.' in filepath else ''
							else:
								ext = '[no extension]'
							extensions.append(ext)
						if extensions:
							counter = Counter(extensions)
							top_3 = counter.most_common(3)
							print(f"{pyfunctions.CYAN}Top extensions{pyfunctions.RESET}")
							for ext, count in top_3:
								print(f"{ext}")
						print() ; directories = [os.path.dirname(filename[0]) for filename in filenames] # top directories
						directory_counts = Counter(directories)
						top_3_directories = directory_counts.most_common(3)
						print(f"{pyfunctions.CYAN}Top 3 directories{pyfunctions.RESET}")
						for directory, count in top_3_directories:
							print(f'{count}: {directory}')
						print() ; cur.execute("SELECT filename FROM logs WHERE TRIM(filename) != ''") # common file 5
						filenames = [row[0] for row in cur.fetchall()]  # end='' prevents extra newlines
						filename_counts = Counter(filenames)
						top_5_filenames = filename_counts.most_common(5)
						print(f"{pyfunctions.CYAN}Top 5 created{pyfunctions.RESET}")
						for file, count in top_5_filenames:
							print(f'{count} {file}')
						top_5_modified = dexec(cur,'Modified', 5)
						filenames = [row[3] for row in top_5_modified]
						filename_counts = Counter(filenames)
						top_5_filenames = filename_counts.most_common(5)
						print(f"{pyfunctions.CYAN}Top 5 modified{pyfunctions.RESET}")
						for filename, count in top_5_filenames:
							filename = filename.strip()
							print(f'{count} {filename}')
						top_7_deleted = dexec(cur,'Deleted', 7)
						filenames = [row[3] for row in top_7_deleted]
						filename_counts = Counter(filenames)
						top_7_filenames = filename_counts.most_common(7)
						print(f"{pyfunctions.CYAN}Top 7 deleted{pyfunctions.RESET}")
						for filename, count in top_7_filenames:
							filename = filename.strip()
							print(f'{count} {filename}')
						top_7_writen = dexec(cur, 'Overwrt', 7)
						filenames = [row[3] for row in top_7_writen]
						filename_counts = Counter(filenames)
						top_7_filenames = filename_counts.most_common(7)
						print(f"{pyfunctions.CYAN}Top 7 overwritten{pyfunctions.RESET}")
						for filename, count in top_7_filenames:
							filename = filename.strip()
							print(f'{count} {filename}')
						top_5_nsf = dexec(cur, 'Nosuchfile', 5)
						filenames = [row[3] for row in top_5_nsf]
						filename_counts = Counter(filenames)
						if filename_counts:
							top_5_filenames = filename_counts.most_common(5)
							print(f"{pyfunctions.CYAN}Not actually a file{pyfunctions.RESET}")
							for filename, count in top_5_filenames:
								print(f'{count} {filename}')
						print() ; print(f"{pyfunctions.GREEN}Filter hits{pyfunctions.RESET}")
						with open('/usr/local/save-changesnew/flth.csv', 'r') as file:
							for line in file:
								print(line, end='')
						if showdb("display database?"):
							if os.environ.get("XDG_SESSION_TYPE") == "wayland":
								print('Wayland session switch to root and call query for display.')
							else:
								disply = os.environ.get('DISPLAY')
								wish_path = shutil.which("wish")
								if disply and wish_path:
									print(f'database in: {tempdir}')
									results(dbopt, conn, cur, dbtarget, email, usr, dbpst)
								elif not wish_path:
									print("Install tk to display db.")
								elif not disply:
									print("No X11 display.")
if __name__ == "__main__":
    main()
