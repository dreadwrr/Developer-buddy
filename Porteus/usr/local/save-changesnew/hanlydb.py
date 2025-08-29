#!/userbin/env python3
# hybrid analysis efficient table queries refined developer buddy  08/28/2025
import codecs
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
def get_recent_changes(filename, cursor):
	cursor.execute('''
	SELECT timestamp, filename, inode, accesstime, checksum, filesize, changetime
	FROM logs
	WHERE filename = ?
	ORDER BY timestamp DESC
	LIMIT 1
	''', (filename,))
	reslt= cursor.fetchone()
	return reslt
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
def parse_datetime(value, fmt="%Y-%m-%d %H:%M:%S"):
	try:
		dt = datetime.strptime(str(value).strip(), fmt)
		return dt.strftime(fmt)
	except (ValueError, TypeError, AttributeError):
		return None
def is_valid_datetime(value, fmt="%Y-%m-%d %H:%M:%S"):
	try: 
		datetime.strptime(str(value).strip(), fmt)
		return True
	except (ValueError, TypeError, AttributeError):
		return False
def collision(filename, checksum, filesize, cursor):
	# cursor.execute('''
	# SELECT a.filename, b.filename, a.checksum, a.filesize, b.filesize
	# FROM logs a
	# JOIN logs b
	# 	ON a.checksum = b.checksum
	# 	AND a.filename != b.filename
	# WHERE a.filesize != b.filesize
	# 	AND a.filename = ?
	# ''', (filename,))
    cursor.execute('''
        SELECT b.filename, a.checksum, a.filesize, b.filesize
        FROM logs a
        JOIN logs b
          ON a.checksum = b.checksum
         AND a.filename != b.filename
        WHERE a.filename = ?
          AND a.checksum = ?
          AND b.filesize != ?
    ''', (filename, checksum, filesize))
    return cursor.fetchall()

def stealth(filename, label, outputf, collision_message, checksum, current_size, original_size, cdiag, option, cursor):
		
	if current_size and original_size:

		file_path=Path(filename)
		if file_path.is_file():
			delta= abs(current_size - original_size)
				
			if original_size == current_size and option != 'eql':  # flag ***
				print(f'Warning file {label} same filesize different checksum. Contents changed.', file=outputf)
				return True
			
			elif delta < 12 and delta != 0:  # stealth cng?
				if label != '/usr/local/save-changesnew/flth.csv':
					message=f'Checksum indicates a change in {label}. Size changed slightly — possible stealth edit.'
					with open('/tmp/scr', 'a') as file8:
						if cdiag == 'true':
							print(f'{message} ({original_size} → {current_size}).', file=file8)
						else:
							print(f'{message}', file=file8)

			if cdiag == 'true' and option != 'eql':
					ccheck=collision(label, checksum, current_size, cursor)
					if ccheck:
						for row in ccheck:
							f1, f2, checksum, size1, size2 = row
							message=f"COLLISION: {f1} vs {f2} | Checksum: {checksum} | Sizes: {size1} != {size2}"
							collision_message.append(message)
						return True

#Hybrid analysis
def hanly(rout, tfile, parsed, checksum, cdiag, cursor):
	csm=False
	collision_message=[]

	with open(rout, 'a') as file, open(tfile, 'a') as file2, open('/tmp/cerr', 'a') as file3:
		for record in parsed:

			label = record[1] # human readable
			filename=codecs.decode(label, 'unicode_escape')
			if not filename:
				continue
			recent_entries = get_recent_changes(label, cursor)
			if not recent_entries:
				continue
			previous  = recent_entries
			filedate = record[0]
			if checksum == 'true':
				if not record[4]: # checksum
					continue  
				current_size = ''
				original_size = ''
				a_size=''
				if is_integer(record[5]):
					current_size = int(record[5] )
					if is_integer(previous[5]):
						original_size = int(previous[5])
			if previous[0] and filedate:
				recent_timestamp =parse_datetime(filedate)
				previous_timestamp = parse_datetime(previous[0])
				if is_integer(record[2]) and is_integer(previous[2]) and recent_timestamp and previous_timestamp:  # inodes


					if recent_timestamp == previous_timestamp: # Not modified?

						if checksum == 'true':
			

							file_path=Path(filename)
							if file_path.is_file():
								result=subprocess.run(['stat','--format=%Y', file_path], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
								asize = subprocess.run(['stat', '--format=%s', file_path], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
								if asize.returncode != 0:
									a_size=int(asize.stdout.strip()) # actual size
								md5=get_md5(file_path)	
								if md5:
									if result.returncode == 0:
										a_mod=int(result.stdout.strip())
										afrm_str = datetime.utcfromtimestamp(a_mod).strftime("%Y-%m-%d %H:%M:%S") # actual modify time
										if afrm_str == previous_timestamp: # stable?
											if is_valid_datetime(record[3]): # format


												if md5 != record[4]:  # Flag ***
													for f in (file, file2, file3):
														print(f'Suspect {record[3]} {label}', file=f)
													csm=True
												else:
													if record[6] != previous[6]:
														for f in (file, file2):
															print(f'Metadata {record[3]} {label}', file=f)


										else:


											if md5 != record[4]:
												if cdiag == 'true': 
													with open('/tmp/scr', 'a') as file6:
														print(f'File changed during the search. {label} at {afrm_str}. Size was {original_size}, now {a_size} ', file=file6)
												else:
													with open('/tmp/scr', 'a') as file6:
														print(f'File changed during search. File likely changed. system cache item.', file=file6)
												csm=stealth(filename, label, file3, collision_message, record[4] , a_size, current_size, cdiag, 'regular', cursor) # Flag *** ?

					else: # Modified.

						if checksum == 'true':


							if record[2] != previous[2]: # Inode


								if record[4] == previous[4]:
									for f in (file, file2):
										print(f'Overwrt {record[3]} {label}', file=f)

										csm=stealth(filename, label, file3, collision_message, record[4], current_size, original_size, cdiag, 'eql', cursor) # stealth edit
								else:
									for f in (file, file2):
										print(f'Replaced {record[3]} {label}', file=f)
									
									csm=stealth(filename, label, file3, collision_message, record[4] ,current_size, original_size, cdiag, 'regular', cursor) # Flag *** ?


							else:


								if record[4] != previous[4]:
									for f in (file, file2):
										print(f'Modified {record[3]} {label}', file=f)
							
									csm=stealth(filename, label, file3, collision_message, record[4] , current_size, original_size, cdiag, 'regular', cursor)  # Flag *** ?
								else:
									for f in (file, file2):
										print(f'Touched {record[3]} {label}', file=f)
						else:
							

							if record[2] != previous[2]:
								for f in (file, file2):
									print(f'Replaced {record[3]} {label}', file=f)
							else: 
								for f in (file, file2):
									print(f'Modified {record[3]} {label}', file=f)	


		if collision_message:
				for entry in collision_message:
					print(entry, file=file3)
	return csm
