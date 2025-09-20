#!/usr/bin/env python3
# pstsrg.py - Process and store logs in a SQLite database, encrypting the database       9/15/2025
import pyfunctions
import os
import shutil
import sqlite3
import subprocess
import sys
from hanlydb import hanly
from hanlyparallel import hanly_parallel
from pyfunctions import getcount
from pyfunctions import parse_line
count=0
def encr(database, opt, email, nc, md):
    try:
            cmd =       [
                  "gpg",
                  "--yes",
                  "--encrypt",
                  "-r", email,
                  "-o", opt,
            ]
            if nc == "true":
                  cmd.extend(["--compress-level", "0"])
            cmd.append(database)
            subprocess.run(cmd, check=True)
            if md == "true":
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
      
def create_table(c, table, last_column, unique_columns):
      columns = [
            'id INTEGER PRIMARY KEY AUTOINCREMENT',
            'timestamp TEXT',
            'filename TEXT',
            'changetime TEXT',
            'inode TEXT',
            'accesstime TEXT',
            'checksum TEXT',
            'filesize TEXT',
            'symlink TEXT',
            'owner TEXT',
            '`group` TEXT',
            'permissions TEXT',
            'casmod TEXT',
            f'{last_column} TEXT'
      ]
      col_str = ',\n      '.join(columns)
      unique_str = ', '.join(unique_columns)
      sql = f'''
      CREATE TABLE IF NOT EXISTS {table} (
      {col_str},
      UNIQUE({unique_str})
      )
      '''
      c.execute(sql)

      sql='CREATE INDEX IF NOT EXISTS'
      
      if table == 'logs':
            c.execute(f'{sql} idx_logs_checksum ON logs (checksum)')
            c.execute(f'{sql} idx_logs_filename ON logs (filename)')
            c.execute(f'{sql} idx_logs_checksum_filename ON logs (checksum, filename)') # Composite
      else:
            c.execute(f'{sql} idx_sys_checksum ON sys (checksum)')
            c.execute(f'{sql} idx_sys_filename ON sys (filename)')
            c.execute(f'{sql} idx_sys_checksum_filename ON sys (checksum, filename)')

def create_db(database, action=None):
      print('Initializing database...')
 
      conn = sqlite3.connect(database)
      c = conn.cursor()
      create_table(c, 'logs', 'hardlinks', ('timestamp','filename', 'changetime')) 

      # c.execute('''
      # CREATE TABLE IF NOT EXISTS stats (
      #       id INTEGER PRIMARY KEY AUTOINCREMENT,
      #       timestamp TEXT,
      #       filename TEXT,
      #       changetime TEXT,
      #       inode TEXT,
      #       accesstime TEXT,
      #       checksum TEXT,
      #       filesize TEXT,
      #       symlink TEXT,
      #       owner TEXT,
      #       `group` TEXT,
      #       permissions TEXT,
      #       casmod TEXT,
      #       hardlinks TEXT,
      #       )
      # ''')

      create_table(c, 'sys', 'count', ('timestamp', 'filename', 'changetime',))

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

def insert(log, conn, c, table, last_column): # Log, sys
      global count
      count = getcount(c)
      # c.executemany('''            original
      #       INSERT OR IGNORE INTO logs (timestamp, filename, changetime, inode, accesstime, checksum, filesize, symlink, owner, `group`, permissions, casmod, hardlinks)
      #       VALUES (Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?))
      # ''', log)
      # blank_row = (None, None, None, None, None, None, None, None, None, None, None, None, None,)  # Blank values for each column in 'logs' table
      # c.execute('''
      #       INSERT INTO logs (timestamp, filename, changetime, inode, accesstime, checksum, filesize, symlink, owner, `group`, permissions, casmod, hardlinks)
      #       VALUES (?, ?, ?, ?, ?, ?, ?, ? ,? ,? ,? ,? ,?)
      # ''', blank_row)
      # conn.commit()
      # if table == 'logs':
            # for record in log:                  logic without UNIQUE fields
            #       filename = record[1]
            #       changetime = record[10]
            #       timestamp = record[0]

            #       c.execute(
            #             "SELECT timestamp FROM logs WHERE filename=? AND changetime=? ORDER BY timestamp DESC LIMIT 1",
            #             (filename, changetime)
            #       )
            #       row = c.fetchone()

            #       if not row or timestamp > row[0]:
            #             # No entry exists, or timestamp is newer → insert
            #             c.execute(
            #                   f"INSERT INTO {table} ({col_str}) VALUES ({', '.join(['?']*len(columns))})",
            #                   record
            #             )
      
      columns = [
            'timestamp', 'filename', 'changetime', 'inode', 'accesstime', 
            'checksum', 'filesize', 'symlink', 'owner', '`group`', 
            'permissions', 'casmod', last_column
      ]
      placeholders = ', '.join(['Trim(?)'] * len(columns))
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

def insert_if_not_exists(action, timestamp, filename, changetime, conn, c): # Stats 
      timestamp = timestamp or None
      c.execute('''
      INSERT OR IGNORE INTO stats (action, timestamp, filename, changetime)
      VALUES (?, ?, ?, ?)
      ''', (action, timestamp, filename, changetime))
      conn.commit()

def parselog(file, list, checksum, type):
      with open(file, 'r') as file: 
            for line in file:
                  inputln = parse_line(line)

                  if not inputln or not inputln[1].strip():
                        continue
            
                  timestamp = None if inputln[0] in ("None", "") else inputln[0]
                  filename    = None if inputln[1] in ("", "None") else inputln[1]
                  changetime  = None if inputln[2] in ("", "None") else inputln[2]
                  inode       = None if inputln[3] in ("", "None") else inputln[3]
                  accesstime = None if inputln[4] in ("", "None") else inputln[4]
                  checks      = None if len(inputln) > 5 and inputln[5] in ("", "None") else (inputln[5] if len(inputln) > 5 else None)
                  filesize    = None if len(inputln) > 6 and inputln[6] in ("", "None") else (inputln[6] if len(inputln) > 6 else None)
                  sym   = None if len(inputln) <= 7 or inputln[7] in ("", "None") else inputln[7]
                  onr   = None if len(inputln) <= 8 or inputln[8] in ("", "None") else inputln[8]
                  gpp   = None if len(inputln) <= 9 or inputln[9] in ("", "None") else inputln[9]
                  pmr   = None if len(inputln) <= 10 or inputln[10] in ("", "None") else inputln[10]
                  cam   = None if len(inputln) <= 11 or inputln[11] in ("", "None") else inputln[11]
                  hardlink_count = None if len(inputln) <= 12 or inputln[12] in ("", "None") else inputln[12]

                  if checksum == 'false':
                        hardlink_count = None if type == "sys" else checks
                        checks=None

                  list.append((timestamp, filename, changetime, inode, accesstime, checks, filesize, sym, onr, gpp, pmr, cam, hardlink_count))

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

def main():
      xdata=sys.argv[1] # data source
      COMPLETE=sys.argv[2] # nsf
      dbtarget=sys.argv[3]  # the target
      rout=sys.argv[4]  # tmp holds action
      tfile=sys.argv[5] # tmp file
      checksum=sys.argv[6] # important
      cdiag=sys.argv[7] # setting
      email=sys.argv[8]
      turbo=sys.argv[9] #mc
      ANALYTICSECT=sys.argv[10]
      ps=sys.argv[11] # proteusshield
      nc=sys.argv[12] # no compression
      user="guest"
      table="logs"
      stats = []
      parsed = []
      parsedsys=[]
      recorddata=[]
      dbe=False
      goahead=True                
      conn=None

      root, ext = os.path.splitext(dbtarget)
      dbopt=root + ".db" # generic output database
      if os.path.isfile(dbtarget):
            sts=decr(dbtarget, dbopt)
            if not sts:
                  print('Find out why db not decrypting or delete it to make a new one')
                  return 2
      else:
            try:
                  conn = create_db(dbopt, True)
                  print(f'{pyfunctions.GREEN}Persistent database created.{pyfunctions.RESET}')
                  goahead=False
            except Exception as e:
                  print("Failed to create db:", e)
      if not conn:                
            conn = sqlite3.connect(dbopt)
      with conn:
            c = conn.cursor()


            parselog(xdata, parsed, checksum, 'sortcomplete') #SORTCOMPLETE/Log

            #initial Sys profile
            if ps != 'false':
                  table="sys"
                  if not table_exists_and_has_data(conn, 'sys') and checksum == 'true':
                        print(f'{pyfunctions.CYAN}Generating system profile from base .xzms.{pyfunctions.RESET}') # hash base xzms
                        result=subprocess.run(["/usr/local/save-changesnew/sysprofile", turbo],capture_output=True,text=True)
                        if result.returncode == 1:
                              print("Bash failed to hash profile.")
                        
                        else:
                              try:
                                    dir_path = result.stdout.strip()

                                    parselog(dir_path, parsedsys, checksum, 'sys') #sys

                                    if os.path.isdir(dir_path):
                                          shutil.rmtree(dir_path)
                              except Exception as e:
                                    print(f"bash sysprofile failed missing SORTCOMPLETE: {e}")


                        if parsedsys:
                              try: 
                                    insert(parsedsys, conn, c, "sys", "count") 
                                    
                              except Exception as e:
                                    print('sys db failed insert', e)
                                    dbe=True


            if parsed:
                  if goahead: # #Hybrid analysis. Skip first pass ect.

                        try: 

                              if turbo == 'mc':
                                    hanly_parallel(rout, tfile, parsed, checksum, cdiag, dbopt, ps, user, dbtarget, table)
                              else:
                                    with open(rout, 'a') as file, open(tfile, 'a') as file2, open('/tmp/cerr', 'a') as file3, open('/tmp/scr', 'a') as file4:
                                          hanly(parsed, recorddata, checksum, cdiag, conn, c,  ps, user, dbtarget, file, file2, file3, file4)
                                          if recorddata:
                                                for record in recorddata:
                                                      timestamp = record[0]
                                                      label = record[1]
                                                      changetime = record[2]
                                                      inode = record[3]   
                                                      checksum = record[5]
                                        
                                                      result = pyfunctions.detect_copy(label, inode, checksum, c, table)
                                                      if result:
                                                            print(f'Copy {record[0]} {record[2]} {label}', file=file)
                                                            

                        except Exception as e:
                              print(f"hanlydb failed to process on mode {turbo}: {e}", file=sys.stderr)
                        if  turbo == 'mc':
                              x=os.cpu_count()
                              if x:
                                    if os.path.isfile('/tmp/cerr'):
                                          with open('/tmp/cerr', 'r') as f:
                                                contents = f.read()
                                          if not ('Suspect' in contents or 'COLLISION' in contents):
                                                print(f'Detected {x} CPU cores.')
                                    else:
                                          print(f'Detected {x} CPU cores.')
                              if ANALYTICSECT:
                                    print(f'{pyfunctions.GREEN}Hybrid analysis on{pyfunctions.RESET}')

            # Log
            if parsed: 
                  try: 
                        insert(parsed, conn, c, "logs", "hardlinks")
                        if count % 10 == 0:
                              print(f'{count + 1} searches in gpg database')

                  except Exception as e:
                        print('log db failed insert', e)
                        dbe=True

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
                        print('stats db failed to insert', e)
                        dbe=True

            if not dbe: # Encrypt if o.k.
                  try:
                        sts=encr(dbopt, dbtarget, email, nc, "true")
                        if not sts:		
                              print(f'Failed to encrypt database. Run   gpg --yes -e -r {email} -o {dbtarget} {dbopt}  before running again.')

                  except Exception as e:
                        print(f'Encryption failed: {e}')
                        return 3 # & 2 gpg problem

                  return 0        
            
            else:
                        

                  if os.path.isfile(dbopt):
                        os.remove(dbopt)
                  return 4 #db problem

if __name__ == "__main__":
      sys.exit(main())
