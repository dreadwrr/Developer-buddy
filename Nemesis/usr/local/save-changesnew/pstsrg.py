#!/usr/bin/env python3
# pstsrg.py - Process and store logs in a SQLite database, encrypting the database       9/26/2025
import csv
import os
import sqlite3
import subprocess
import sys
import sysprofile
import tempfile
import time
from hanlyparallel import hanly_parallel
from io import StringIO
from rntchangesfunctions import getnm
from pyfunctions import unescf_py
from pyfunctions import getcount
from pyfunctions import cprint

count=0

def dict_string(data: list[dict]) -> str:
    if not data:
        return ""
    
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys(), delimiter='|', quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()

# enc mem
def encrm(c_data: str, opt: str, r_email: str, compress: bool = True, armor: bool = False) -> bool:
      try:
            cmd = [
            "gpg",
            "--batch",
            "--yes",
            "--encrypt",
            "-r", r_email,
            "-o", opt
            ]

            if not compress:
                  cmd.extend(["--compress-level", "0"])

            if armor:
                  cmd.append("--armor")

            result = subprocess.run(
                  cmd,
                  input=c_data.encode("utf-8"),
                  check=True,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE,
            )
            return True

      except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode().strip() if e.stderr else str(e)
            print(f"[ERROR] Encryption failed: {err_msg}")
            return False

# dec mem
def decrm(src):
      if os.path.isfile(src):
            try:
                  cmd = [
                        "gpg",
                        "--quiet",
                        "--batch",
                        "--yes",
                        "--decrypt",
                        src
                  ]
                  result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                  return result.stdout 
            except subprocess.CalledProcessError as e:
                  print(f"[ERROR] Decryption failed: {e}")
                  return None
      else:
            print('No .gpg file')
            return None
    
def encr(database, opt, email, nc, md):
    try:
            cmd =       [
                  "gpg",
                  "--yes",
                  "--encrypt",
                  "-r", email,
                  "-o", opt,
            ]
            if nc:
                  cmd.extend(["--compress-level", "0"])
            cmd.append(database)
            subprocess.run(cmd, check=True)
            if md:
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
            'lastmodified TEXT',
            f'{last_column} TEXT',
            'escapedpath TEXT' 
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
      #       lastmodified TEXT,
      #       hardlinks TEXT,
      #       escapedpath TEXT
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
      
      columns = [
            'timestamp', 'filename', 'changetime', 'inode', 'accesstime', 
            'checksum', 'filesize', 'symlink', 'owner', '`group`', 
            'permissions', 'casmod', 'lastmodified', last_column, 'escapedpath'
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


def main(xdata, COMPLETE, dbtarget, rout, checksum, cdiag, email, ANALYTICSECT, ps, nc, user='guest'):

      table="logs"
      parsed = []
      parsedsys=[]
      dbe=False
      goahead=True                
      conn=None
      dbopt=getnm(dbtarget, 'db')

      with tempfile.TemporaryDirectory(dir='/tmp') as tempdir:
            dbopt=os.path.join(tempdir, dbopt)

            if os.path.isfile(dbtarget):
                  sts=decr(dbtarget, dbopt)
                  if not sts:
                        print('Find out why db not decrypting or delete it to make a new one')
                        return
            else:
                  try:
                        conn = create_db(dbopt, True)
                        cprint.green('Persistent database created')
                        goahead=False
                  except Exception as e:
                        print("Failed to create db:", e)
            if not conn:                
                  conn = sqlite3.connect(dbopt)
            with conn:
                  c = conn.cursor()

                  parsed=xdata

                  # Proteus shield initial Sys profile
                  if ps:
                        table="sys"
                        if not table_exists_and_has_data(conn, table) and checksum:
                              cprint.cyan('Generating system profile from base .xzms.') 

                              try:
                                    parsedsys = sysprofile.main() # hash base xzms
                                    
                              except Exception as e:
                                    print(f'sysprofile.py failed to hash. {e}')
                                    parsedsys = None


                              if parsedsys:
                                    try: 
                                          insert(parsedsys, conn, c, "sys", "count") 
                                          
                                    except Exception as e:
                                          print('sys db failed insert', e)
                                          dbe=True

                  # Log
                  if parsed:
                        if goahead: # Hybrid analysis. Skip first pass ect.

                              try: 
                                    
                  
                                    hanly_parallel(rout, parsed, checksum, cdiag, dbopt, ps, user, dbtarget, table)

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
                                          cprint.green('Hybrid analysis on')


                              except Exception as e:
                                    print(f"hanlydb failed to process : {e}", file=sys.stderr)

                  
                        try: 
                              insert(parsed, conn, c, "logs", "hardlinks")
                              if count % 10 == 0:
                                    print(f'{count + 1} searches in gpg database')

                        except Exception as e:
                              print('log db failed insert', e)
                              dbe=True

                  # Stats
                  if rout: 

                        if COMPLETE: # store no such files
                              rout.extend([" ".join(map(str, item)) for item in COMPLETE])
                            #rout.extend(" ".join(map(str, item)) for item in COMPLETE)

                        try:
                              for record in rout:
                                    parts = record.strip().split(None, 5)
                                    if len(parts) < 6:
                                          continue
                                    action = parts[0]
                                    timestamp = f'{parts[1]} {parts[2]}'
                                    changetime = f'{parts[3]} {parts[4]}'
                                    fp_escaped = parts[5]
                                    fp = unescf_py(fp_escaped) 
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

                  else:
                              
                        if os.path.isfile(dbopt):
                              os.remove(dbopt)
                        print(f'There is a problem with the database.')

if __name__ == "__main__":
      main()
