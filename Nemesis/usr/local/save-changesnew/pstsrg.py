#!/usr/bin/env python3 
# pstsrg.py - Process and store logs in a SQLite database, encrypting the database       8/14/2025
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
      
      # elif act == 'stats':         original
      #       c.executemany('''
      #             INSERT OR IGNORE INTO stats (action, timestamp, filename)
      #             VALUES (?, ?, ?)
      #       ''', log)
      #       c.execute('''
      #       SELECT action, timestamp, filename FROM stats ORDER BY rowid DESC LIMIT 1
      #       ''')
      #       last_row = c.fetchone()
      #       if last_row:
      #             action, timestamp, filename = last_row
      #             if action == '' and timestamp == '' and filename == '':
      #                   # Blank row is already at the bottom, no need to insert it again
      #                   print("Blank row already at the bottom.")
      #             else:
      #                   # Insert blank row at the bottom
      #                   blank_row = ('', '', '')
      #                   c.execute('''
      #                         INSERT INTO stats (action, timestamp, filename)
      #                         VALUES (?, ?, ?)
      #                   ''', blank_row)
      #       else:
      #             # No rows in the table, insert the first blank row
      #             blank_row = ('', '', '')
      #             c.execute('''
      #                   INSERT INTO stats (action, timestamp, filename)
      #                   VALUES (?, ?, ?)
      #             ''', blank_row)

      conn.commit()
      conn.close()


def insert_if_not_exists(action, timestamp, filename):

      conn = sqlite3.connect(dbopt)  # Replace with your actual database file path
      c = conn.cursor()
      #if action == 'Nosuchfile': #insert to keep count###
      #      c.execute('''
      #            INSERT INTO stats (action, timestamp, filename)
      #            VALUES (?, ?, ?)
      #      ''', (action, timestamp, filename))     
      #      conn.commit()

      #else:
            # Check if the record already exists based on timestamp and filename
            #c.execute('''
            #SELECT 1 FROM stats WHERE timestamp = ? AND filename = ?
            #''', (timestamp, filename))

            # If no row is returned, insert the new record
            #if not c.fetchone():
      timestamp = timestamp or None
      c.execute('''
      INSERT OR IGNORE INTO stats (action, timestamp, filename)
      VALUES (?, ?, ?)
      ''', (action, timestamp, filename))
      conn.commit()
      conn.close()

def parse_line(line):
      # Extract the quoted path (first quoted string)
      quoted_match = re.search(r'"(.*?)"', line)
      if not quoted_match:
            return None  # or raise an error / return empty list

      filepath = quoted_match.group(1)
      line_without_file = line.replace(f'"{filepath}"', '').strip() # Remove the quoted part
      other_fields = line_without_file.split()     # Split the remaining fields by whitespace

      timestamp1 = other_fields[0] + ' ' + other_fields[1]
      inode = other_fields[2]
      timestamp2 = other_fields[3] + ' ' + other_fields[4]
      rest = other_fields[5:]

      # Combine: timestamp1,  timestamp2
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

      #target=sys.argv[1] # to gpg file tgt
      xdata=sys.argv[1] # data source    
      act=sys.argv[2] .strip() # action            
      #email=sys.argv[3]
      #clvl = None # compression  

      if act == 'log':
            
            try:
                  with open(xdata, 'r') as record: # from our search  SORTCOMPLETE
  
                        logs = []
                        for line in record:
                             
                              #match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) "([^"]+)" (\d+) (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ([a-f0-9]+) (\d+)', line)
                              parsed = parse_line(line)

                              if not parsed:
                                    continue

                              timestamp = parsed[0]
                              filename = parsed[1]
                              inode = parsed[2]
                              accesstime = parsed[3]
                              checksum = parsed[4]  # if len(parsed) > 4 else None
                              filesize = parsed[5]   #if len(parsed) > 5 else None
                  
                              # timestamp = parsed.group(0)
                              # filename = parsed.group(1)
                              # inode = parsed.group(2)
                              # accesstime = parsed.group(3)
                              # checksum = parsed.group(4) if len(parsed) > 4 else None
                              # filesize = parsed.group(5) if len(parsed) > 5 else None
                        
                              #timestampObject = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                              #accesstimeObject = datetime.strptime(accesstime, '%Y-%m-%d %H:%M:%S')
                              #formatted_timestamp = timestampObject.strftime('%Y-%m-%d %H:%M:%S')
                              #formatted_accesstime = accesstimeObject.strftime('%Y-%m-%d %H:%M:%S')

                              logs.append((timestamp, filename, inode, accesstime, checksum, filesize))

                        if logs:

                              insert(logs)
                              
            except Exception as e:
                  print('log db failed insert', e)
                  sys.exit(2)
            
      if act == 'stats':
            logs = []
#                        for line in record:
#                              if not line.strip():
#                                    continue
#                              #match = re.match(r'(\w+),?"([\d\- :]+)",?"([^"]+)"', line.strip())
#                              if match:
#                                    action = match.group(1)
#                                    timestamp = match.group(2)
#                                    filename = match.group(3)
		
            try:                                              
                  with open(xdata, 'r', newline='') as record:

                        for line in record:
                              line = line.strip()
                              if not line:
                                    continue  # skip empty lines
                              parts = line.split(",", 2)  # split at the first two commas only
                              action = parts[0].strip()
                              datetime = parts[1].strip() #if len(parts) > 1 else ""
                              filepath = parts[2].strip()          #if len(parts) > 2 else ""
                              if filepath:						
                                    logs.append((action, datetime, filepath))

                  if logs:
                        for record in logs:
                              action = record[0]  
                              timestamp = record[1]  
                              filename = record[2]  

                              insert_if_not_exists(action, timestamp, filename) # Call the function to check if the record exists and insert if not #insert(logs)
                               
            except Exception as e:
                  print('stats db failed to insert', e)
                  sys.exit(2)
      print(count)
