# hybrid analysis efficient table queries refined developer buddy  09/5/2025
import codecs
import stat
import pyfunctions
from datetime import datetime, timedelta
from pathlib import Path

def stealth(filename, label, cer, scr, collision_message, checksum, current_size, original_size, cdiag, option, cursor):
		
	if current_size and original_size:

		file_path=Path(filename)
		if file_path.is_file():
			delta= abs(current_size - original_size)
				
			if original_size == current_size and option != 'eql':  # flag ***
				print(f'Warning file {label} same filesize different checksum. Contents changed.', file=cer)

			elif delta < 12 and delta != 0:  # stealth cng?
				message=f'Checksum indicates a change in {label}. Size changed slightly — possible stealth edit.'
				
				if cdiag == 'true':
					print(f'{message} ({original_size} → {current_size}).', file=scr)
				else:
					print(f'{message}', file=scr)

			if cdiag == 'true' and option != 'eql':
				ccheck=pyfunctions.collision(label, checksum, current_size, cursor, 'logs')
				if ccheck:
					for row in ccheck:
						b_filename, a_checksum, a_filesize, b_filesize = row
						message=f"COLLISION: {b_filename} | Checksum: {a_checksum} | Sizes: {a_filesize} != {b_filesize}"
						collision_message.append(message)

#Hybrid analysis
def hanly(parsed, checksum, cdiag, conn, c, ps, usr, dbtarget, file, file2, file3, file4):

	collision_message=[]
	fmt = "%Y-%m-%d %H:%M:%S"

	for record in parsed:
		df=False
		is_sys=False
		recent_sys = None
		label = record[1] # human readable
		try: 
			filename=codecs.decode(label, 'unicode_escape')
			if not filename:
				raise ValueError("Empty filename")
		except Exception as e:
			print(f"Skipping label due to decode file: {label} error: {e}")
			continue

		recent_entries = pyfunctions.get_recent_changes(label, c, 'logs')

		if ps == 'true':
			recent_sys = pyfunctions.get_recent_changes(label, c, 'sys')
		
		if not recent_entries and not recent_sys:
			continue

		filedate = record[0]
		previous = recent_entries

		if ps == 'true':  # hand off previous record to system?
			recent_timestamp = pyfunctions.parse_datetime(filedate)
			if recent_sys:
				if recent_sys:
					recent_systime = pyfunctions.parse_datetime(recent_sys[0])
					if recent_systime:
						if recent_systime > recent_timestamp:
							is_sys=True
							pyfunctions.increment_fname(conn, c, label) # add to system file count db
							previous = recent_sys
							filedate = recent_systime

		if not recent_entries or not previous or not filedate or not previous[0]:
			continue

		if checksum == 'true':
			if not record[4] or str(record[4]).strip() == '': # checksum
				continue
			current_size = None
			original_size = None
			if pyfunctions.is_integer(record[5]):
				current_size = int(record[5])
				if pyfunctions.is_integer(previous[5]):
					original_size = int(previous[5])
						
		recent_timestamp = pyfunctions.parse_datetime(filedate)     # Format check. pick inodes
		previous_timestamp = pyfunctions.parse_datetime(previous[0])
		if pyfunctions.is_integer(record[2]) and pyfunctions.is_integer(previous[2]) and recent_timestamp and previous_timestamp:


			if recent_timestamp == previous_timestamp: # Not modified?

				if checksum == 'true':
	
					try:
						file_path=Path(filename)
						if file_path.is_file():
							
							md5=pyfunctions.get_md5(file_path)
							st = file_path.stat()
							a_size = st.st_size
							a_mod = int(st.st_mtime)


							if md5:
								afrm_str = datetime.utcfromtimestamp(a_mod).strftime(fmt) # actual modify time
								afrm_dt = pyfunctions.parse_datetime(afrm_str)               
                                
								if afrm_dt and pyfunctions.is_valid_datetime(record[3]): # stable? format?

									if afrm_dt == previous_timestamp:
										


										if md5 != record[4]:  # Flag ***
											for f in (file, file2, file3):
												print(f'Suspect {record[0]} {label}', file=f)
												print(f'Suspect file: {label} changed without a new modified time.', file3)
												df=True
								

								else:



									if md5 != record[4]:
										if cdiag == 'true': 
											print(f'File changed during the search. {label} at {afrm_str}. Size was {original_size}, now {a_size} ', file=file4)
										else:
											print(f'File changed during search. File likely changed. system cache item.', file=file4)
										stealth(filename, label, file3, file4, collision_message, record[4] , a_size, current_size, cdiag, 'regular', c) # Flag *** ?
										df=True



								if not df:
									a_ctime = int(st.st_ctime)
									ctime_str = datetime.utcfromtimestamp(a_ctime).strftime(fmt)
									mode_str = stat.filemode(st.st_mode)
									uid_str = str(st.st_uid)
									metadata = (mode_str, uid_str, st.st_gid, a_size, a_mod, ctime_str)			

									prev_ctime = datetime.strptime(metadata[5], fmt)
									recent_ctime = datetime.strptime(str(record[10]).strip(), fmt)

									metadata_changed = (
										metadata[0] != str(record[9]).strip() or # Perm
										metadata[1] != str(record[7]).strip() or # Owner
										metadata[2] != int(record[8]) or # Group
										prev_ctime != recent_ctime # metadata[5]
									)
									if metadata_changed:
										for f in (file, file2):
											print(f'Metadata {record[0]} {label}', file=f)

				
					except Exception as e:
						print(f"Skipping {filename}: {type(e).__name__} - {e}")
						continue

			else: # Modified.

				if checksum == 'true':


					if record[2] != previous[2]: # Inode



						if record[4] == previous[4]:
							for f in (file, file2):
								print(f'Overwrite {record[0]} {label}', file=f)
							stealth(filename, label, file3, file4, collision_message, record[4], current_size, original_size, cdiag, 'eql', c) # stealth edit

						else:
							for f in (file, file2):
								print(f'Replaced {record[0]} {label}', file=f)
							stealth(filename, label, file3, file4, collision_message, record[4] ,current_size, original_size, cdiag, 'regular', c) # Flag *** ?


					else:



						if record[4] != previous[4]:
							for f in (file, file2):
								print(f'Modified {record[0]} {label}', file=f)
							stealth(filename, label, file3, file4, collision_message, record[4] , current_size, original_size, cdiag, 'regular', c)  # Flag *** ?
						else:
							for f in (file, file2):
								print(f'Touched {record[0]} {label}', file=f)


				else:
					


					if record[2] != previous[2]:
						for f in (file, file2):
							print(f'Replaced {record[0]} {label}', file=f)
					else: 
						for f in (file, file2):
							print(f'Modified {record[0]} {label}', file=f)	



				two_days_ago = datetime.now() - timedelta(days=2)
				if previous_timestamp < two_days_ago:
					message=f'File that isnt regularly updated {label}.'
					if is_sys:
						print(f'{message} and is a system file.', file=file4)
					else:
						screen = pyfunctions.get_delete_patterns(usr, dbtarget)
						if not pyfunctions.matches_any_pattern(label, screen):		
							print(f'{message}.', file=file4)				


	if collision_message:
		for entry in collision_message:
			print(entry, file=file3)
