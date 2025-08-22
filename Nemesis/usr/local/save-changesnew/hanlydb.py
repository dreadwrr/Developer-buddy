#!/userbin/env python3
# hybrid analysis efficient table queries refined developer buddy  08/14/2025
import codecs
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
def get_recent_changes(filename, cursor):
	cursor.execute('''
	SELECT Trim(timestamp), Trim(filename), Trim(inode), Trim(accesstime), Trim(checksum), Trim(filesize)
	FROM logs
	WHERE filename = ?
	ORDER BY timestamp DESC
	LIMIT 1
	''', (filename,))
	recent_entries = cursor.fetchall()
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


# Stealth edits / file collision
def stealth(file, original_size, current_size, label, diag, csum):

	result=subprocess.run(['stat','--format=%Y', file], text=True)
	a_mod=int(result.stdout.strip())
	afrm=datetime.utcfromtimestamp(a_mod) #UTC

	if result.returncode == 0:  # still exists
		if original_size and current_size:

			delta= abs(current_size - original_size)
			if delta < 3 and delta != 0:
				# stealth cng
				with open('/tmp/scr', 'a') as file3:
					print(f'Checksum indicates a change in ${label}. Size changed slightly — possible stealth edit. ({original_size} → {current_size}.', file=file3) 

			elif delta == 0 and csum == "csum":
				# flag ***
				with open('/tmp/cerr', 'a') as file4:
					print(f'File collision {label}. Same modified date and checksum. Either md5 is too weak or file was edited and matches exact checksum.', file=file4) 

#Hybrid analysis
def hanly(rout, tfile, parsed, checksum, cdiag, cursor):

	csm=False

	with open(rout, 'a') as file, open(tfile, 'a') as file2, open('/tmp/cerr', 'a') as file3:

		for record in parsed:

			label = record[1] # human readable escaped
			filename=codecs.decode(label, 'unicode_escape')

			if not filename:
				continue
			recent_entries = get_recent_changes(label, cursor)
			if  not recent_entries:
				continue

			previous  = recent_entries[0] # start parsing
			filedate = record[0]
		
			if previous[0] and filedate:

				recent_timestamp = datetime.strptime(filedate, "%Y-%m-%d %H:%M:%S")
				previous_timestamp = datetime.strptime(previous[0], "%Y-%m-%d %H:%M:%S")

				if is_integer(record[2]) and is_integer(previous[2]):  # If we have both inodes
					if recent_timestamp == previous_timestamp:

						if checksum == 'true':
								
								if is_valid_datetime(record[3]) and is_valid_datetime(previous[3]): # Access time ensures currect format
									if is_integer(record[4]) and is_integer(previous[4]): # Both have inodes?
											if current_size and original_size: # Perfect format

												# Checksum cng
												if record[4] != previous[4]:     

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
																	# User will get alert on the console
																	message=f'Csumc {recent_timestamp} {label}'
																	print(message, file=file)        # rout
																	print(message, file=file2)    #  tout
																	print(message, file=file3)     #  cer     <---- Flag
																	csm=True

																else:

																	current_checksum=record[4]
																	# Change during search
																	if md5 != current_checksum and cdiag == 'true':  # Output to file instead of notify
																		with open('/tmp/scr', 'a') as file6:
																			print(f'File changed during the search. {label} at {afrm}. Size was {original_size}, now {current_size} ', file=file6)
																	elif md5 != current_checksum:
																		with open('/tmp/scr', 'a') as file6:
																			print(f'File changed during search. File likely changed. system cache item.', file=file6) # Notify

												# Same checksum
												else: # File collision ?
													stealth(filename, original_size, current_size, label, cdiag) 
					# Regular
					else:  

						# Inode
						if record[2] != previous[2]: 

							if checksum == 'true': # More detail

								if is_valid_datetime(record[3]) and is_valid_datetime(previous[3]): # Access time ensures format
									if record[4] and previous[4]: # checksum good format

										# Checksum
										if record[4] == previous[4]:   

											print(f'Overwrt {recent_timestamp} {label}', file=file)
											print(f'Overwrt {recent_timestamp} {label}', file=file2)

										# Checksum cng
										else:
											original_size = previous[5]
											current_size = record[5]

											if current_size and original_size:
												stealth(filename, original_size, current_size, label, cdiag) # detail anomalies

											print(f'Replaced {recent_timestamp} {label}', file=file)   # Normal
											print(f'Replaced {recent_timestamp} {label}', file=file2)

							else:  # We have just given more info with Inode change
								print(f'Replaced {recent_timestamp} {label}', file=file)
								print(f'Replaced {recent_timestamp} {label}', file=file2)
								
						# Same Inode
						else: 
							if checksum == 'true': # more detail
								if is_valid_datetime(record[3]) and is_valid_datetime(previous[3]):
									if record[4] and previous[4]:

										# Checksum cng
										if record[4] != previous[4]: 

											original_size = previous[5] # the database
											current_size = record[5]  # from our search

											if current_size and original_size:
												stealth(filename, original_size, current_size, label, cdiag) # detail anomalies

											print(f'Modified {recent_timestamp} {label}', file=file)
											print(f'Modified {recent_timestamp} {label}', file=file2)


										else: #slight same same meta
											print(f'Touched {recent_timestamp} {label}', file=file)
											print(f'Touched {recent_timestamp} {label}', file=file2)

							else: # Normal event
								print(f'Modified {recent_timestamp} {label}', file=file)
								print(f'Modified {recent_timestamp} {label}', file=file2)

	return csm
