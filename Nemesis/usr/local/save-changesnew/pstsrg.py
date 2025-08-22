#!/usr/bin/env python3
# pstsrg.py - Process and store logs in a SQLite database, encrypting the database       8/14/2025
import pyfunctions
import os
import sqlite3
import subprocess
import sys
from hanlydb import hanly
from pyfunctions import getcount
from pyfunctions import parse_line
count=0
def encr(database, opt, email, md):
    try:
        subprocess.run([
            "gpg",
            "--yes",
            "--encrypt",
            "-r", email,
            "-o", opt,
            database
        ], check=True)
        #print(f"File encrypted: {output_path}")
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

# initialize a db
def create_db(database):
      print('Initializing database...')
      conn = sqlite3.connect(database)
      c = conn.cursor()
      c.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  filename TEXT,
                  inode TEXT,
                  accesstime TEXT,
                  checksum TEXT,
                  filesize TEXT,
                  UNIQUE(timestamp, filename)
            )
      ''')
      c.execute('''
      CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            timestamp TEXT,
            filename TEXT,
			UNIQUE(timestamp, filename)
            )
      ''') 
      conn.commit()
      return (conn)
# Log insert
def insert(log, conn, c):
      global count
      count = getcount(c) #First count the number of blank rows
      c.executemany('''
            INSERT OR IGNORE INTO logs (timestamp, filename, inode, accesstime, checksum, filesize)
            VALUES (Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?))
      ''', log)
      blank_row = (None, None, None, None, None, None)  # Blank values for each column in 'logs' table
      c.execute('''
            INSERT INTO logs (timestamp, filename, inode, accesstime, checksum, filesize)
            VALUES (?, ?, ?, ?, ?, ?)
      ''', blank_row)
      conn.commit()
# Stats insert
def insert_if_not_exists(action, timestamp, filename, conn, c):
      timestamp = timestamp or None
      c.execute('''
      INSERT OR IGNORE INTO stats (action, timestamp, filename)
      VALUES (?, ?, ?)
      ''', (action, timestamp, filename))
      conn.commit()
def main():

      xdata=sys.argv[1] # data source
      nfs=sys.argv[2] # more stats
      dbtarget=sys.argv[3]  # the target
      rout=sys.argv[4]  # tmp holds action
      tfile=sys.argv[5] # tmp file
      checksum=sys.argv[6] # important
      cdiag=sys.argv[7] # setting
      email=sys.argv[8]
      turbo=sys.argv[9]

      logs = []
      stats = []
      parsed = []
      csm=False # from bash nothing flagged yet
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

            conn = create_db(dbopt)
            print(f'{pyfunctions.GREEN}Persistent database created.{pyfunctions.RESET}')
            goahead=False

      if not conn:
            conn = sqlite3.connect(dbopt)

      with conn:
            c = conn.cursor()

            #SORTCOMPLETE
            with open(xdata, 'r') as file:

                  for line in file:
                        inputln = parse_line(line)

                        if not inputln:
                              continue

                        if not inputln[1].strip():
                              continue

                        timestamp = inputln[0].strip() if inputln[0] else None
                        filename = inputln[1].strip() if inputln[1] else None
                        inode = inputln[2].strip() if inputln[2] else None
                        accesstime = inputln[3].strip() if inputln[3] else None
                        checksum = inputln[4].strip() if len(inputln) > 4 and inputln[4] else None
                        filesize = inputln[5].strip() if len(inputln) > 5 and inputln[5] else None

                        parsed.append((timestamp, filename, inode, accesstime, checksum, filesize))

            if parsed:
                  if goahead: # Skip first pass ect.

                        #Hybrid analysis
                        try:

                              csm=hanly(rout, tfile, parsed, checksum, cdiag, c)

                              if  csm:

                                    with open("/tmp/cerr", "r") as f:

                                          for line in f:
                                                print(f'{pyfunctions.RED}*** Checksum of file altered without a modified time {line}', end='')

                                    os.remove("/tmp/cerr")

                              else:

                                    if  turbo == 'mc':
                                          x=os.cpu_count()

                                          if x:
                                                print(f'Detected {x} CPU cores.')
                                    print(f'{pyfunctions.GREEN}Hybrid analysis on{pyfunctions.RESET}')
                        except:
                              print('hanlydb failed to process', file=sys.stderr)

            # Log
            try:

                  if parsed:

                        insert(parsed, conn, c)
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
                                    parts = line.split(maxsplit=3)
                                    if len(parts) < 4:
                                          continue

                                    
                                    action = parts[0]
                                    date = parts[1]
                                    time = parts[2]
                                    fp = parts[3] 
                                    filename = fp.strip()

                                    if filename:

                                          stats.append((action, date + ' ' + time, filename))

                        if stats:

                              for record in stats:

                                    action = record[0]
                                    timestamp = record[1]
                                    fp = record[2]

                                    insert_if_not_exists(action, timestamp, fp, conn, c)

                  except Exception as e:
                        print('stats db failed to insert', e)
                        dbe=True

            # Encrypt if o.k.
            if not dbe:
                  
                  try:

                        sts=encr(dbopt, dbtarget, email, True)
                        if not sts:
                              print(f'Failed to encrypt database. Run   gpg --yes -e -r {email} -o {dbtarget} {dbopt}  before running again.')
                              
                  except Exception as e:
                        print(f'Encryption failed: {e}')
                        return 3
                  
                  return 0
            
            else:
                  return 4

if __name__ == "__main__":
      sys.exit(main())
