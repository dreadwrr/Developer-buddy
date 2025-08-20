#!/userbin/env python3
# hybrid analysis efficient table queries refined developer buddy  08/14/2025
import csv
import hashlib
import re
import os
import sqlite3
import subprocess
import sys
import time 
from pstsrg import parse_line
from datetime import datetime
from pathlib import Path

xdata=sys.argv[1]  # the source
nfs=sys.argv[2] # more stats
database=sys.argv[3]  # the target
rout=sys.argv[4]  # tmp holds action
tfile=sys.argv[5] # tmp file 
checksum=sys.argv[6] # important
cdiag=sys.argv[7] # setting
recent = []  # the recent entry to compare to ify any
parsed = [] # from file SORTCOMPLETE
csm=False # from bash nothing flagged yet

def get_recent_changes(filename):

    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT timestamp, filename, inode, accesstime, checksum, filesize
        FROM logs
        WHERE filename = ?
        ORDER BY timestamp DESC
        LIMIT 1
    ''', (filename,))

    recent_entries = cursor.fetchall()
    conn.close()

    return recent_entries

def get_md5(file_path):
    try:
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None
def is_integer(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False
def is_valid_datetime(value, fmt="%Y-%m-%d %H:%M:%S"):
    try:
        datetime.strptime(value, fmt)
        return True
    except (ValueError, TypeError):
        return False

def stealth(file, original_size, current_size, label, diag, csum):

	result=subprocess.run(['stat','--format=%Y', file], text=True) 
	a_mod=int(result.stdout.strip()) # epoch
	afrm=datetime.utcfromtimestamp(a_mod)  #UTC fmt
	if result.returncode == 0:  # still exists

		if original_size and current_size:
			delta= abs(current_size - original_size)
			if delta < 3 and delta != 0:
				with open('/tmp/scr', 'a') as file3:
					print(f'Checksum indicates a change in ${label}. Size changed slightly — possible stealth edit. ({original_size} → {current_size}.', file=file3)
			elif delta == 0 and csum == "csum":
				with open('/tmp/cerr', 'a') as file4:
					print(f'File collision {label}. Same modified date and checksum. Either md5 is too weak or file was edited and matches exact checksum.', file=file4) # flag

#Hybrid analysis
def hanly():

	with open(rout, 'a') as file, open(tfile, 'a') as file2, open('/tmp/cerr', 'a') as file3, open('/home/guest/aris', 'w') as file4:
		for record in parsed:

			label = record[1] # human readable
			filename=label.replace("\\n", "\n") # for files with \n in their name
			filedate = record[0]
			if not filename:
				continue
		  
			recent_entries = get_recent_changes(label) # get the most recent entry
		    
			if len(recent_entries) < 1:
				continue

			previous = recent_entries[0] # start parsing
			
			recent_timestamp = datetime.strptime(filedate, "%Y-%m-%d %H:%M:%S")
			previous_timestamp = datetime.strptime(previous[0], "%Y-%m-%d %H:%M:%S")
			if is_integer(record[2]) and is_integer(previous[2]):  # If we have both inodes

				if recent_timestamp == previous_timestamp:
					if checksum == 'true':
							if is_valid_datetime(record[3]) and is_valid_datetime(previous[3]):
								if is_integer(record[4]) and is_integer(previous[4]): # Both have inodes?


										if current_size and original_size: # Perfect format
											if record[4] != previous[4]:     # checksum cng
												file_path=Path(filename)
												if file_path.is_file(): # File didnt disapear
													result=subprocess.run(['stat','--format=%Y', file_path], text=True) 
													md5 = get_md5(file_path)
													original_size = previous[5]
													current_size = record[5]

													if md5:
														if result.returncode == 0:  # still exists ensure we have all the data
															a_mod=int(result.stdout.strip()) # epoch
															afrm=datetime.utcfromtimestamp(a_mod)  # UTC
															if afrm == recent_timestamp: # If the file is steady
																message=f'Csumc {recent_timestamp} {label}'  # Flag
																print(message, file=file)        # rout
																print(message, file=file2)    #  tout
																print(message, file=file3)     #  scr     user will get alert on the console
																
																csm=True
 
															else:

																current_checksum=record[4]
																if md5 != current_checksum and cdiag == 'true':
																	with open('/tmp/scr', 'a') as file6:
																		print(f'File changed during the search. {label} at {afrm}. Size was {original_size}, now {current_size} ', file=file6)
																elif md5 != current_checksum:
																	with open('/tmp/scr', 'a') as file6:
																		print(f'File changed during search. File likely changed. system cache item.', file=file6)
												else:
													stealth(filename, original_size, current_size, label, cdiag) # File collision 
										

				else:  # Regular but What changed?
					
					if record[2] != previous[2]: # inode
						if checksum == 'true':
						
							if record[4] and previous[4]: # checksum good format

								if record[4] == previous[4]:  # more detail
									print(f'Overwrt {recent_timestamp} {label}', file=file)
									print(f'Overwrt {recent_timestamp} {label}', file=file2)
									#print(f'Overwrt {recent_timestamp} {label}', file=file4)
									
								else:
									original_size = previous[5]
									current_size = record[5]

									if current_size and original_size:
										stealth(filename, original_size, current_size, label, cdiag) # detail anomalies 

									print(f'Replaced {recent_timestamp} {label}', file=file)   # Normal
									print(f'Replaced {recent_timestamp} {label}', file=file2)
									#print(f'Replaced {recent_timestamp} {label}', file=file4)

						else:  # We have just given more info than the diff file with Inode change       Norm
							print(f'Replaced {recent_timestamp} {label}', file=file)       #rout
							print(f'Replaced {recent_timestamp} {label}', file=file2)       #tout							
							#print(f'Replaced {recent_timestamp} {label}', file=file4)
					
					else: # Same Inode
						if checksum == 'true': # more detail
							#print('thatbranch')
							if record[4] and previous[4]:

								if record[4] != previous[4]: # checksum cng

									original_size = previous[5] # the database 
									current_size = record[5]  # from our search

									if current_size and original_size:
										stealth(filename, original_size, current_size, label, cdiag) # detail anomalies 

									print(f'Modified {recent_timestamp} {label}', file=file)
									print(f'Modified {recent_timestamp} {label}', file=file2)
									#print(f'Modified {recent_timestamp} {label}', file=file4)

								else: #slight same same
									print(f'Touched {recent_timestamp} {label}', file=file)
									print(f'Touched {recent_timestamp} {label}', file=file2)     
									#print(f'Touched {recent_timestamp} {label}', file=file4)
						else: # We have different time and indication of change. normal event less detail
							print(f'Modified {recent_timestamp} {label}', file=file)
							print(f'Modified {recent_timestamp} {label}', file=file2)      
							#print(f'Modified {recent_timestamp} {label}', file=file4) 
                     
# main 
if __name__ == "__main__":

	with open(xdata, 'r') as file:
		for line in file:
			inputln = parse_line(line)

			if not inputln:
				continue

			timestamp = inputln[0]
			filename = inputln[1]
			inode = inputln[2]
			accesstime = inputln[3]
			checksum = inputln[4] if len(inputln) > 4 else None
			filesize = inputln[5] if len(inputln) > 5 else None

			# regex and flatten tupples
			parsed.append([
				timestamp,	
				filename, 
				inode,
				accesstime,
				checksum,
				filesize
			])

	hanly() 
	if  csm:
		print('csm')
