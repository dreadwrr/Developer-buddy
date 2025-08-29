#!/usr/bin/env python3
# pstsrg.py - Process and store logs in a SQLite database, encrypting the database       8/28/2025
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
                  symlink TEXT,
                  owner TEXT,
                  `group` TEXT,
                  permissions TEXT,
                  changetime TEXT,
                  casmod TEXT,
                  hardlinks TEXT,
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
# Log 
def insert(log, conn, c):
      global count
      count = getcount(c) #First count the number of blank rows

      c.executemany('''
            INSERT OR IGNORE INTO logs (timestamp, filename, inode, accesstime, checksum, filesize, symlink, owner, `group`, permissions, changetime, casmod, hardlinks)
            VALUES (Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?), Trim(?))
      ''', log)

      blank_row = (None, None, None, None, None, None, None, None, None, None, None, None,None,)  # Blank values for each column in 'logs' table
      c.execute('''
            INSERT INTO logs (timestamp, filename, inode, accesstime, checksum, filesize, symlink, owner, `group`, permissions, changetime, casmod, hardlinks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ? ,? ,? ,? ,? ,?)
      ''', blank_row)
      conn.commit()
# Stats 
def insert_if_not_exists(action, timestamp, filename, conn, c):
      timestamp = timestamp or None
      c.execute('''
      INSERT OR IGNORE INTO stats (action, timestamp, filename)
      VALUES (?, ?, ?)
      ''', (action, timestamp, filename))
      conn.commit()
def main():

      xdata=sys.argv[1] # data source
      dbtarget=sys.argv[2]  # the target
      rout=sys.argv[3]  # tmp holds action
      tfile=sys.argv[4] # tmp file                  if parsed and inf:               
      checksum=sys.argv[5] # important
      cdiag=sys.argv[6] # setting
      email=sys.argv[7]
      turbo=sys.argv[8]
      ANALYTICSECT=sys.argv[9]
      hlinks=sys.argv[10]
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

            with open(xdata, 'r') as file: #SORTCOMPLETE

                  for line in file:
                        inputln = parse_line(line)
                        if not inputln:
                              continue
                        if not inputln[1].strip():
                               continue
                        timestamp = inputln[0] if inputln[0] else ''
                        filename = inputln[1] if inputln[1] else ''
                        inode = inputln[2] if inputln[2] else ''
                        accesstime = inputln[3] if inputln[3] else ''
                        checks = inputln[4] if len(inputln) > 4 and inputln[4] else ''
                        filesize = inputln[5] if len(inputln) > 5 and inputln[5] else None
                        if checksum == 'true':
                            sym = inputln[6]  if inputln[6] else ''
                            onr = inputln[7]  if len(inputln) > 7  and inputln[7]  else ''
                            gpp = inputln[8]  if len(inputln) > 8  and inputln[8]  else ''
                            pmr = inputln[9]  if len(inputln) > 9  and inputln[9]  else ''
                            itime = (inputln[10] + ' ' + inputln[11]) if len(inputln) > 11 and inputln[10] and inputln[11] else ''
                            cam = inputln[12] if len(inputln) > 12 and inputln[12] else ''
                            hardlink_count=inputln[13] if len(inputln) > 13 and inputln[13] else ''
                        else:
                            sym = ''
                            onr = ''
                            gpp = ''
                            pmr = ''
                            itime = ''
                            cam = ''
                            hardlink_count=checks
                            checks=''
                        parsed.append((timestamp, filename, inode, accesstime, checks, filesize, sym, onr, gpp, pmr, itime, cam, hardlink_count))

            if parsed:
                  if goahead: # Skip first pass ect.

                        try: #Hybrid analysis
                              csm=hanly(rout, tfile, parsed, checksum, cdiag, c)

                        except Exception as e:  # Catch any exception and store it in 'e'
                              print(f"hanlydb failed to process: {e}", file=sys.stderr)  # Print the error message

                        if not csm:
                              if  turbo == 'mc':
                                    x=os.cpu_count()
                                    if x:
                                          print(f'Detected {x} CPU cores.')
                              if ANALYTICSECT:
                                    print(f'{pyfunctions.GREEN}Hybrid analysis on{pyfunctions.RESET}')
            
            try: # Log

                  if parsed:
                        insert(parsed, conn, c)
                        if count % 10 == 0:
                              print(f'{count + 1} searches in gpg database')

            except Exception as e:
                  print('log db failed insert', e)
                  dbe=True

            if os.path.isfile(rout): # Stats

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

            if not dbe: # Encrypt if o.k.
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
