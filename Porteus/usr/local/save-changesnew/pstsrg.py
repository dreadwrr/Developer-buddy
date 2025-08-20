#!/usr/bin/env python3 
# pstsrg.py - Process and store logs in a SQLite database, encrypting the database       8/14/2025
import codecs
import csv
import os
import re
import sqlite3
import subprocess
import sys
import time
from pyfunctions import getcount
from datetime import datetime
from subprocess import CalledProcessError

count=0 

# initialize a db
def create_db(database):   

      conn = sqlite3.connect(database)
      c = conn.cursor()

      #if act == 'log':
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

     # elif act == 'stats':
      c.execute('''
      CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            timestamp TEXT,
            filename TEXT,
			UNIQUE(timestamp, filename)
            )
      ''') #UNIQUE(action, timestamp, filename) 
                  
      conn.commit()
      conn.close()

# convert
def insert(log):
     
      global count
      conn = sqlite3.connect(dbopt)
      c = conn.cursor()

      #if act == 'log':   original
      count = getcount(c) #First count the number of blank rows
            
      c.executemany('''
            INSERT OR IGNORE INTO logs (timestamp, filename, inode, accesstime, checksum, filesize)
            VALUES (?, ?, ?, ?, ?, ?)
      ''', log)

      blank_row = (None, None, None, None, None, None)  # Blank values for each column in 'logs' table
      c.execute('''
            INSERT INTO logs (timestamp, filename, inode, accesstime, checksum, filesize)
            VALUES (?, ?, ?, ?, ?, ?)
      ''', blank_row)
      
      conn.commit()
      conn.close()


def insert_if_not_exists(action, timestamp, filename):

      conn = sqlite3.connect(dbopt)
      c = conn.cursor()

      timestamp = timestamp or None
      c.execute('''
      INSERT OR IGNORE INTO stats (action, timestamp, filename)
      VALUES (?, ?, ?)
      ''', (action, timestamp, filename))
      conn.commit()
      conn.close()

def parse_line(line):
     
      quoted_match = re.search(r'"((?:[^"\\]|\\.)*)"', line)
      if not quoted_match:
            return None
      raw_filepath = quoted_match.group(1)

      try:
            filepath = codecs.decode(raw_filepath.encode(), 'unicode_escape')
            #print(f"Decoded filepath: {filepath}")

      except UnicodeDecodeError as e:
            #print(f"Error decoding filepath: {e}")
            return None
      
      line_without_file = line.replace(quoted_match.group(0), '').strip()
      other_fields = line_without_file.split()
      if len(other_fields) < 5:
            return None  # Not enough fields

      timestamp1 = other_fields[0] + ' ' + other_fields[1]
      inode = other_fields[2]
      timestamp2 = other_fields[3] + ' ' + other_fields[4]
      rest = other_fields[5:]

      return [timestamp1, filepath, inode, timestamp2] + rest


if __name__ == "__main__":

      dr='/usr/local/save-changesnew/'
      dbtarget=dr + 'recent.gpg' # target encrypted file
      dbopt=dr + 'recent.db' # generic output database
      sys.stdout = open("/tmp/debug.log", "a")
      sys.stderr = sys.stdout

      if "--init" in sys.argv:
            create_db(dbopt) # if there isnt one
            sys.exit(0) 

      xdata=sys.argv[1] # data source    
      act=sys.argv[2] .strip() # action            

      if act == 'log':
            
            try:
                  with open(xdata, 'r') as record:
  
                        logs = []
                        for line in record:
                             
                              parsed = parse_line(line)

                              if not parsed:
                                    continue

                              logs.append(tuple(parsed))

                              #logs.append((timestamp, filename, inode, accesstime, checksum, filesize))

                        if logs:

                              insert(logs)
                              
            except Exception as e:
                  print('log db failed insert', e)
                  sys.exit(2)
            
      if act == 'stats':
            logs = []

            try:                                              
                  with open(xdata, 'r', newline='') as record:

                        for line in record:
                              line = line.strip()
                              if not line:
                                    continue
                              parts = line.split(",", 2)  # split at the first two commas only
                              if len(parts) < 2:
                                    continue
                              action = parts[0].strip()
                              datetime = parts[1].strip() #if len(parts) > 1 else ""
                              fp = parts[2].strip()          #if len(parts) > 2 else ""

                              if fp:

                                    try:
                                          filepath = codecs.decode(fp, 'unicode_escape')

                                    except Exception:
                                          filepath = fp  # fallback if decoding fails		
                                          				
                                    logs.append((action, datetime, filepath))

                  if logs:
                        for record in logs:
                              action = record[0]  
                              timestamp = record[1]  
                              filename = record[2]  

                              insert_if_not_exists(action, timestamp, filename)
                               
            except Exception as e:
                  print('stats db failed to insert', e)
                  sys.exit(2)
      print(count)
