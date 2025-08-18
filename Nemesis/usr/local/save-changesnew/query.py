#!/userbin/env python3
import os
import shutil
import string
import subprocess
import sqlite3
import sys
import tempfile
import tkinter as tk
import time

from collections import Counter
from datetime import datetime
from pyfunctions import getcount
from tkinter import ttk  
#email='john.doe@email.com'
dr='/usr/local/save-changesnew'
#logopt='recent.db' #output database
#statopt='stats.db'
dbtarget='recent.gpg' # has everything stats logpst table
xdata='logs.db'

CYAN = "\033[36m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m" 

sort_directions = {}

def sort_column(tree, col, columns):
    global sort_directions

    # Get index of the column to sort by
    index = columns.index(col)

    # Toggle sort direction (default ascending)
    ascending = sort_directions.get(col, True)
    sort_directions[col] = not ascending

    # Get all items currently in the tree
    data = [(tree.set(child, col), child) for child in tree.get_children('')]

    def convert(value):
        if col == "filesize":
            try:
                return int(value)
            except (ValueError, TypeError):
                return -1  # Treat blank or invalid as -1
        else:
            return value.lower() if isinstance(value, str) else value

    # Sort data based on converted value
    data.sort(key=lambda t: convert(t[0]), reverse=not ascending)

    # Rearrange items in the treeview
    for index_, (val, item) in enumerate(data):
        tree.move(item, '', index_)


def dencr(gpgfile, database):

    if not os.path.isfile(gpgfile):
        print(f"Input file does not exist: {gpgfile}")
        sys.exit(2)

    cmd = ["gpg", "--yes", "-d", "-o", database, gpgfile]

    try:
        subprocess.run(
            cmd,
            check=True,
        )
        print(f"GPG decryption successful: {database}")

    except subprocess.CalledProcessError as e:
        print("GPG decryption failed!")
        print("Return code:", e.returncode)
        sys.exit(2)
    except Exception as e:
        print("Unexpected error during decryption:", e)
        sys.exit(2)

def results(database):

    import sqlite3
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("SELECT * FROM logs")
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    conn.close()

    root = tk.Tk()
    root.title("Database Viewer")

    tree = ttk.Treeview(root, columns=columns, show='headings')
    tree.pack(expand=True, fill=tk.BOTH)

    for col in columns:
        tree.heading(col, text=col, command=lambda _col=col: sort_column(tree, _col, columns))
        if col == "filename":
            tree.column(col, width=1000)      # bigger filename
        elif col == "id":
            tree.column(col, width=50)       # smaller id
        elif col == "timestamp":
            tree.column(col, width=150)      # a bit bigger timestamp
        elif col == "accesstime":
            tree.column(col, width=150)      # a bit bigger accesstime
        elif col == "checksum":
            tree.column(col, width=270)      # a bit bigger checksum
        else:
            tree.column(col, width=100)      # default width

    for row in rows:
        tree.insert('', tk.END, values=row)

    root.mainloop()


        # #create_db(output)

        # #stats

def averagetm(database):

    conn = sqlite3.connect(database)
    cur = conn.cursor()

    cur.execute('''
    SELECT timestamp
    FROM logs
    ORDER BY timestamp ASC
    ''')

    timestamps = cur.fetchall()
    conn.close()

    total_minutes = 0
    valid_timestamps = 0

    for timestamp in timestamps:

        if timestamp and timestamp[0]:

            current_time = datetime.strptime(timestamp[0], "%Y-%m-%d %H:%M:%S")
            total_minutes += current_time.hour * 60 + current_time.minute
            valid_timestamps += 1

    if valid_timestamps > 0: #average time in minutes
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

    # log pst db
    
        # db Test  starting point
        # print(opt)
        #conn = sqlite3.connect(opt)
        #cur = conn.cursor()
        # cur.execute("SELECT COUNT(*) FROM logs;")
        # count = cur.fetchone()[0]
        # print("Number of rows in logs:", count)
        # conn.close()
    with tempfile.TemporaryDirectory(dir="/tmp") as tempdir:
        output=os.path.join(tempdir, xdata) #tmp area
        dencr(dr +"/" + dbtarget, output)
        opt=tempdir + "/" + xdata # our decrypted db       

        #time.sleep(555)

        if os.path.isfile(opt):
            # Search breakdown
            atime=averagetm(opt)
            print(f"{CYAN}Search breakdown{RESET}")
            print(f'Avg hour of activity: {atime}')
            conn = sqlite3.connect(opt) # Calculate the average filesize
            cur = conn.cursor()
            cnt = getcount(cur)
            cur.execute('''
            SELECT filesize
            FROM logs
            ''')
            filesizes = cur.fetchall()
            conn.close()
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

            conn = sqlite3.connect(opt)   # top directories      
            cur = conn.cursor()
            cur.execute('''
            SELECT filename 
            FROM logs
            WHERE TRIM(filename) != ''
            ''')
            filenames = cur.fetchall()
       
            directories = [os.path.dirname(filename[0]) for filename in filenames]
            directory_counts = Counter(directories)
            top_3_directories = directory_counts.most_common(3)
            print(f"{CYAN}Top 3 directories{RESET}")
            for directory, count in top_3_directories:
                print(f'{count}: {directory} times')
            print()
            
            conn = sqlite3.connect(opt)  # common file 5
            cur = conn.cursor()
            cur.execute("SELECT filename FROM logs WHERE TRIM(filename) != ''") 
            filenames = [row[0] for row in cur.fetchall()]
            conn.close()
            filename_counts = Counter(filenames)
            top_5_filenames = filename_counts.most_common(5)
            print(f"{CYAN}Top 5 created{RESET}")
            for file, count in top_5_filenames:
                print(f'{count} {file}')
            # most replaced by inode
            # conn = sqlite3.connect(opt)
            # cur = conn.cursor()
            # cur.execute("SELECT inode, filename FROM logs")  
            # rows = cur.fetchall()
            # conn.close()
            # inodes = [row[1] for row in rows] 
            # inode_counts = Counter(inodes)
            # top_5_inodes = inode_counts.most_common(5)

            # print(f"{GREEN}Top 5 replaced by inode{RESET}")
            # #print("Top 5 Inodes:", top_5_inodes)
            # for inode, count in top_5_inodes:
            #     print(f'{count} {inode}')
            
            conn = sqlite3.connect(opt)  # Top 5 mod
            cur = conn.cursor()
            cur.execute('''
            SELECT * 
            FROM stats
            WHERE action = 'Modified'
            ORDER BY timestamp DESC
            LIMIT 5
            ''')
            top_5_modified = cur.fetchall()
            conn.close()
            filenames = [row[3] for row in top_5_modified]
            filename_counts = Counter(filenames)
            top_5_filenames = filename_counts.most_common(5)
            print(f"{CYAN}Top 5 modified{RESET}")
            for filename, count in top_5_filenames:
                print(f'{count} {filename}')        
            conn = sqlite3.connect(opt)  # Top 7 del
            cur = conn.cursor()
            cur.execute('''
            SELECT * 
            FROM stats
            WHERE action = 'Deleted'
            ORDER BY timestamp DESC
            LIMIT 7
            ''')
            top_7_deleted = cur.fetchall()
            conn.close()
            filenames = [row[3] for row in top_7_deleted]
            filename_counts = Counter(filenames)
            top_7_filenames = filename_counts.most_common(7)
            print(f"{CYAN}Top 7 deleted{RESET}")
            for filename, count in top_7_filenames:
                print(f'{count} {filename}')        
            conn = sqlite3.connect(opt)  # Top 7 ovwrite
            cur = conn.cursor()
            cur.execute('''
            SELECT * 
            FROM stats
            WHERE action = 'Overwrt'
            ORDER BY timestamp DESC
            LIMIT 7
            ''')
            top_7_writen = cur.fetchall()
            conn.close()
            filenames = [row[3] for row in top_7_writen]
            filename_counts = Counter(filenames)
            top_7_filenames = filename_counts.most_common(7)
            print(f"{CYAN}Top 7 overwritten{RESET}")
            for filename, count in top_7_filenames:
                print(f'{count} {filename}')        
            conn = sqlite3.connect(opt)  # Top 5 no such file
            cur = conn.cursor()
            cur.execute('''
            SELECT * 
            FROM stats
            WHERE action = 'Nosuchfile'
            ORDER BY timestamp DESC
            LIMIT 5
            ''')
            top_5_nsf = cur.fetchall()
            conn.close()
            filenames = [row[3] for row in top_5_nsf]
            filename_counts = Counter(filenames)
            if filename_counts:
                top_5_filenames = filename_counts.most_common(5)
                print(f"{CYAN}Not actually a file{RESET}")
                for filename, count in top_5_filenames:
                    print(f'{count} {filename}')        
            print()
            print(f"{RED}Filter hits{RESET}")
            with open('/usr/local/save-changesnew/flth.csv', 'r') as file:
                for line in file:
                    print(line, end='')  # end='' prevents extra newlines
            #Results?
            if showdb("display database?"):
                if os.environ.get("XDG_SESSION_TYPE") == "wayland":
                    print('Wayland session switch to root and call query for display.')
                else:
                    disply = os.environ.get('DISPLAY')
                    wish_path = shutil.which("wish")
                    if disply and wish_path:
                        results(opt)
                    else:
                        print(f'To view database dowload tk from package manager. Or leave this session up and use sqlitebrowser and go to: {tempdir}')
                
            else:
                print("You chose no")

if __name__ == "__main__":
 
    main()






