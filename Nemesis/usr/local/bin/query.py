#!/userbin/env python3
import os
import pyfunctions
import shutil
import sqlite3
import sys
import tempfile
import tkinter as tk
from pstsrg import decr
from pstsrg import encr
from collections import Counter
from datetime import datetime
from pyfunctions import getcount
from tkinter import ttk
sort_directions = {}
def clear_cache(database, target, email, conn, cur):
    files_d = [ # Delete patterns db
    "%caches%",
    "%cache2%",
    "%cache%",
    "%Cache2%",
    "%.cache%",
    "%share/Trash%",
]
    for filename_pattern in files_d:
        try:
            cur.execute("DELETE FROM logs WHERE filename LIKE ?", (filename_pattern,))
            conn.commit()
            cur.execute("DELETE FROM stats WHERE filename LIKE ?", (filename_pattern,))
            conn.commit()
        except Exception as e:
            print(f"Unable to write to database: {e}")
    try:
        encr(database, target, email, False)
        print("Cache files cleared.")
    except sqlite3.Error as e:
        print("Failed to write to db.")
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
def results(database, conn, cur, target, email):
    #with sqlite3.connect(database) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM logs")
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        root = tk.Tk()
        root.title("Database Viewer")
        frame = tk.Frame(root)
        frame.pack(fill=tk.X)
        clear_cache_button = tk.Button(frame, text="Clear Cache", command=lambda: clear_cache(database, target, email, conn, cur))
        clear_cache_button.pack(side=tk.RIGHT, padx=10, pady=10)
        tree = ttk.Treeview(root, columns=columns, show='headings')
        tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10)
        scrollbar = tk.Scrollbar(root, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)
        for col in columns:
            tree.heading(col, text=col, command=lambda _col=col: sort_column(tree, _col, columns))
            if col == "filename":
                tree.column(col, width=1000)
            elif col == "id":
                tree.column(col, width=50)
            elif col == "timestamp":
                tree.column(col, width=150)
            elif col == "accesstime":
                tree.column(col, width=150)
            elif col == "checksum":
                tree.column(col, width=270)
            else:
                tree.column(col, width=100)
        for row in rows:
            tree.insert('', tk.END, values=row)
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
	output = os.path.splitext(os.path.basename(dbtarget))[0]
	with tempfile.TemporaryDirectory(dir='/tmp') as tempdir:
		dbopt=os.path.join(tempdir, output + '.db')
		if decr(dbtarget, dbopt):
				if os.path.isfile(dbopt):
					with sqlite3.connect(dbopt) as conn:
						cur = conn.cursor()
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
							if filesize and filesize[0]:  # Check if filesize is valid (not None or blank)
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
						''')
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
							# Ext
							print(f"{pyfunctions.CYAN}Top extensions{pyfunctions.RESET}")
							for ext, count in top_3:
								print(f"{ext}")
							print()
						# top directories
						directories = [os.path.dirname(filename[0]) for filename in filenames]
						directory_counts = Counter(directories)
						top_3_directories = directory_counts.most_common(3)
						print(f"{pyfunctions.CYAN}Top 3 directories{pyfunctions.RESET}")
						for directory, count in top_3_directories:
							print(f'{count}: {directory} times')
						print()
					# common file 5
						cur.execute("SELECT filename FROM logs WHERE TRIM(filename) != ''")
						filenames = [row[0] for row in cur.fetchall()]  # end='' prevents extra newlines
						filename_counts = Counter(filenames)
						top_5_filenames = filename_counts.most_common(5)
						print(f"{pyfunctions.CYAN}Top 5 created{pyfunctions.RESET}")
						for file, count in top_5_filenames:
							print(f'{count} {file}')
						# Top 5 mod
						cur.execute('''
						SELECT *
						FROM stats
						WHERE action = 'Modified'
						ORDER BY timestamp DESC
						LIMIT 5
						''')
						top_5_modified = cur.fetchall()
						filenames = [row[3] for row in top_5_modified]
						filename_counts = Counter(filenames)
						top_5_filenames = filename_counts.most_common(5)
						print(f"{pyfunctions.CYAN}Top 5 modified{pyfunctions.RESET}")
						for filename, count in top_5_filenames:
							filename = filename.strip()
							print(f'{count} {filename}')
						# Top 7 del
						cur.execute('''
						SELECT *
						FROM stats
						WHERE action = 'Deleted'
						ORDER BY timestamp DESC
						LIMIT 7
						''')
						top_7_deleted = cur.fetchall()
						filenames = [row[3] for row in top_7_deleted]
						filename_counts = Counter(filenames)
						top_7_filenames = filename_counts.most_common(7)
						print(f"{pyfunctions.CYAN}Top 7 deleted{pyfunctions.RESET}")
						for filename, count in top_7_filenames:
							filename = filename.strip()
							print(f'{count} {filename}')
						# Top 7 ovwrite
						cur.execute('''
						SELECT *
						FROM stats
						WHERE action = 'Overwrt'
						ORDER BY timestamp DESC
						LIMIT 7
						''')
						top_7_writen = cur.fetchall()
						filenames = [row[3] for row in top_7_writen]
						filename_counts = Counter(filenames)
						top_7_filenames = filename_counts.most_common(7)
						print(f"{pyfunctions.CYAN}Top 7 overwritten{pyfunctions.RESET}")
						for filename, count in top_7_filenames:
							filename = filename.strip()
							print(f'{count} {filename}')
						# Top 5 no such file
						cur.execute('''
						SELECT *
						FROM stats
						WHERE action = 'Nosuchfile'
						ORDER BY timestamp DESC
						LIMIT 5
						''')
						top_5_nsf = cur.fetchall()
						filenames = [row[3] for row in top_5_nsf]
						filename_counts = Counter(filenames)
						if filename_counts:
							top_5_filenames = filename_counts.most_common(5)
							print(f"{pyfunctions.CYAN}Not actually a file{pyfunctions.RESET}")
							for filename, count in top_5_filenames:
								print(f'{count} {filename}')
						print()
						print(f"{pyfunctions.GREEN}Filter hits{pyfunctions.RESET}")
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
									results(dbopt, conn, cur, dbtarget, email)

if __name__ == "__main__":
    main()
