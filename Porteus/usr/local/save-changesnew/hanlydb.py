# hybrid analysis efficient table queries refined developer buddy  09/5/2025
import codecs
import stat
import pyfunctions
import pwd
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
def hanly(parsed, recorddata, checksum, cdiag, conn, c, ps, usr, dbtarget, file, file2, file3, file4):

	collision_message=[]
	ra=False
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
			recorddata.append(record)
			continue

		filedate = record[0]
		previous = recent_entries

		if ps == 'true':  # check sys
			recent_timestamp = pyfunctions.parse_datetime(filedate, fmt)
			if recent_sys:
				if recent_sys:
					recent_systime = pyfunctions.parse_datetime(recent_sys[0], fmt)
					if recent_systime:
						if recent_systime > recent_timestamp:
							is_sys=True
							ra=True
							pyfunctions.increment_fname(conn, c, label) # add to system file count db
							previous = recent_sys
							filedate = recent_systime

		if not recent_entries or not previous or not filedate or not previous[0]:
			continue

		if checksum == 'true':
			if not record[5] or str(record[5]).strip() == '': # checksum
				continue
			current_size = None
			original_size = None
			if pyfunctions.is_integer(record[6]):
				current_size = int(record[6])
				if pyfunctions.is_integer(previous[6]):
					original_size = int(previous[6])
						
		recent_timestamp = pyfunctions.parse_datetime(filedate, fmt)
		previous_timestamp = pyfunctions.parse_datetime(previous[0], fmt)
		if pyfunctions.is_integer(record[3]) and pyfunctions.is_integer(previous[3]) and recent_timestamp and previous_timestamp:


			if recent_timestamp == previous_timestamp: # Not modified?

				if checksum == 'true':
	
					try:
						file_path=Path(filename)
						if file_path.is_file():
							
							md5=pyfunctions.get_md5(file_path)
							st = file_path.stat()
							a_size = st.st_size
							a_mod = int(st.st_mtime)
							#a_ctime = int(st.st_ctime)
							#ctime_str = datetime.utcfromtimestamp(a_ctime).strftime(fmt)
							mode_str = stat.filemode(st.st_mode)
							uid_str = pwd.getpwuid(st.st_uid).pw_name
							#str(st.st_uid) # , ctime_str
							metadata = (mode_str, uid_str, st.st_gid, a_size, a_mod)

							if md5:
								afrm_str = datetime.utcfromtimestamp(a_mod).strftime(fmt) # actual modify time
								afrm_dt = pyfunctions.parse_datetime(afrm_str, fmt)               
                        
								if afrm_dt and pyfunctions.is_valid_datetime(record[2], fmt): # stable? format?

									if afrm_dt == previous_timestamp:
										

										if md5 != record[5]:  # Flag ***
											print(f'Suspect {record[0]} {record[2]} {label}', file=file)
											print(f'Suspect {record[0]} {label}', file=file2)
											print(f'Suspect file: {label} changed without a new modified time.', file3)
											df=True
								

								else:


									if md5 != record[5]:
										if cdiag == 'true': 
											print(f'File changed during the search. {label} at {afrm_str}. Size was {original_size}, now {a_size} ', file=file4)
										else:
											print(f'File changed during search. File likely changed. system cache item.', file=file4)
										stealth(filename, label, file3, file4, collision_message, record[5], a_size, current_size, cdiag, 'regular', c) # Flag *** ?
										df=True



								if not df:


									if record[3] == previous[3]: # Inode

										#prev_ctime = datetime.strptime(metadata[5], fmt)
										#recent_ctime = datetime.strptime(str(record[2]).strip(), fmt)

										metadata = (metadata[0], metadata[1], metadata[2], metadata[3], metadata[4])
										metadata_changed = (
											metadata[0] != str(record[10]).strip() or # Perm
											metadata[1] != str(record[8]).strip() or # Owner
											metadata[2] != int(record[9]) # Group
										)	

										if metadata_changed:
											print(f'Metadata {record[0]} {record[2]} {label}', file=file)
											print(f'Metadata {record[0]} {label}', file=file2)
										df=True


					except Exception as e:
						print(f"Skipping {filename}: {type(e).__name__} - {e}")
						continue

			else: # Modified.

				df=True

				if checksum == 'true':


					if record[3] != previous[3]: # Inode


						if record[5] == previous[5]:
							print(f'Overwrite {record[0]} {record[2]} {label}', file=file)
							print(f'Overwrite {record[0]} {label}', file=file2)
							stealth(filename, label, file3, file4, collision_message, record[5], current_size, original_size, cdiag, 'eql', c) # stealth edit

						else:
							print(f'Replaced {record[0]} {record[2]} {label}', file=file)
							print(f'Replaced {record[0]} {label}', file=file2)
							stealth(filename, label, file3, file4, collision_message, record[5] ,current_size, original_size, cdiag, 'regular', c) # Flag *** ?
							

					else:


						if record[5] != previous[5]:
							print(f'Modified {record[0]} {record[2]} {label}', file=file)
							print(f'Modified {record[0]} {label}', file=file2)
							stealth(filename, label, file3, file4, collision_message, record[5] , current_size, original_size, cdiag, 'regular', c)  # Flag *** ?
						else:			
							print(f'Touched {record[0]} {record[2]} {label}', file=file)
							print(f'Touched {record[0]} {label}', file=file2)
						

				else:
					

					if record[3] != previous[3]:
						print(f'Replaced {record[0]} {record[2]} {label}', file=file)
						print(f'Replaced {record[0]} {label}', file=file2)
					else: 

						print(f'Modified {record[0]} {record[2]} {label}', file=file)
						print(f'Modified {record[0]} {label}', file=file2)	
					

				two_days_ago = datetime.now() - timedelta(days=2)
				if previous_timestamp < two_days_ago:
					message=f'File that isnt regularly updated {label}.'
					if is_sys:
						print(f'{message} and is a system file.', file=file4)
					else:
						screen = pyfunctions.get_delete_patterns(usr, dbtarget)
						if not pyfunctions.matches_any_pattern(label, screen):		
							print(f'{message}.', file=file4)

			if not df:	
				recorddata.append(record)
	if ra:
		conn.commit()
	if collision_message:
		for entry in collision_message:
			print(entry, file=file3)
