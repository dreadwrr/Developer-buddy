
# hybrid analysis  9/5/2025
import codecs
from datetime import datetime, timedelta
import sqlite3
import stat
from pathlib import Path
from pyfunctions import collision
from pyfunctions import is_integer
from pyfunctions import is_valid_datetime
from pyfunctions import increment_fname
from pyfunctions import get_delete_patterns
from pyfunctions import get_md5
from pyfunctions import get_recent_changes
from pyfunctions import matches_any_pattern
from pyfunctions import parse_datetime

def stealth(filename, label, entry, checksum, collision_message, current_size, original_size, cdiag, option, cursor, is_sys):

	if current_size and original_size:
		file_path=Path(filename)
		if file_path.is_file():
			delta= abs(current_size - original_size)
				

			if original_size == current_size and option != 'eql':
				entry["cerr"].append(f'Warning file {label} same filesize different checksum. Contents changed.')
			

			elif delta < 12 and delta != 0:
					message=f'Checksum indicates a change in {label}. Size changed slightly — possible stealth edit.'
					

					if cdiag == 'true':                                                    
						entry["scr"].append(f'{message} ({original_size} → {current_size}).')
					else:
						entry["scr"].append(message)


			if cdiag == 'true' and option != 'eql':
					ccheck=collision(label, checksum, current_size, cursor, is_sys)

					if ccheck:
						for row in ccheck:
							b_filename, a_checksum, a_filesize, b_filesize = row
							collision_message.append(f"COLLISION: {b_filename} | Checksum: {a_checksum} | Sizes: {a_filesize} != {b_filesize}")
						

def hanly(parsed_chunk, checksum, cdiag, dbopt, ps, usr, dbtarget):

	fmt = "%Y-%m-%d %H:%M:%S"
	results = []
	conn = sqlite3.connect(dbopt)
	with conn:
		cursor = conn.cursor()

		for record in parsed_chunk:

			entry = {"cerr": [], "flag": [], "scr": [], "sys": []}
			collision_message=[]
			is_sys=False
			df=False
			recent_sys = None
			label = record[1]
			try: 
				filename=codecs.decode(label, 'unicode_escape')
				if not filename:
					raise ValueError("Empty filename")
			except Exception as e:
				print(f"Skipping label due to decode file: {label} error: {e}")
				continue
			
			recent_entries = get_recent_changes(label, cursor, 'logs')

			if ps == 'true':
				recent_sys = get_recent_changes(label, cursor, 'sys')
			
			if not recent_entries and not recent_sys:
				continue

			filedate = record[0]
			previous = recent_entries

			if ps == 'true':  # hand off previous record to system?
				recent_timestamp = parse_datetime(filedate)
				if recent_sys:
					if recent_sys:
						recent_systime = parse_datetime(recent_sys[0])
						if recent_systime:
							if recent_systime > recent_timestamp:
								is_sys=True
								increment_fname(conn, cursor, label) # add to system file count db

								previous = recent_sys
								filedate = recent_systime

			if not recent_entries or not previous or not filedate or not previous[0]:
				continue

			if checksum == 'true':
				if not record[4] or str(record[4]).strip() == '': # checksum
					continue
				current_size = None
				original_size = None
				if is_integer(record[5]):
					current_size = int(record[5])
					if is_integer(previous[5]):
						original_size = int(previous[5])

			recent_timestamp = parse_datetime(filedate)
			previous_timestamp = parse_datetime(previous[0])
			if is_integer(record[2]) and is_integer(previous[2]) and recent_timestamp and previous_timestamp:

				if recent_timestamp == previous_timestamp:

					if checksum == 'true':
		
						
						try:
							file_path=Path(filename)
							if file_path.is_file():
								md5=get_md5(file_path)
								st = file_path.stat()
								a_size = st.st_size
								a_mod = int(st.st_mtime)

															
								if md5:
									afrm_str = datetime.utcfromtimestamp(a_mod).strftime(fmt) # actual modify time
									afrm_dt = parse_datetime(afrm_str)               
											
									if afrm_dt and is_valid_datetime(record[3]): # Format check.

										if afrm_dt == previous_timestamp:
							

											if md5 != record[4]:
												entry["flag"].append(f'Suspect {record[0]} {label}')
												entry["cerr"].append(f'Suspect file: {label} changed without a new modified time.')
												df=True


									else:


										if md5 != record[4]:
											if cdiag == 'true': 
												entry["scr"].append(f'File changed during the search. {label} at {afrm_str}. Size was {original_size}, now {a_size}')
											else:
												entry["scr"].append(f'File changed during search. File likely changed. system cache item.')
											stealth(filename, label, entry, record[4], collision_message, a_size, current_size, cdiag, 'regular', cursor, is_sys)
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
											entry["flag"].append(f'Metadata {record[0]} {label}')


						except Exception as e:
							print(f"Skipping {filename}: {type(e).__name__} - {e}")
							continue

				else:

					if checksum == 'true':


						if record[2] != previous[2]:


							if record[4] == previous[4]:
								entry["flag"].append(f'Overwrt {record[0]} {label}')
								stealth(filename, label, entry, record[4], collision_message,current_size, original_size, cdiag, 'eql', cursor, is_sys)
							else:
								entry["flag"].append(f'Replaced {record[0]} {label}')
								stealth(filename, label, entry, record[4], collision_message, current_size, original_size, cdiag, 'regular', cursor, is_sys)


						else:


							if record[4] != previous[4]:
								entry["flag"].append(f'Modified {record[0]} {label}')
								stealth(filename, label, entry, record[4], collision_message, current_size, original_size, cdiag, 'regular', cursor, is_sys)
							else:
								entry["flag"].append(f'Touched {record[0]} {label}')


					else:
						

						if record[2] != previous[2]:
							entry["flag"].append(f'Replaced {record[0]} {label}')	
						else: 
							entry["flag"].append(f'Modified {record[0]} {label}')
								

					two_days_ago = datetime.now() - timedelta(days=2)
					if previous_timestamp < two_days_ago:
						message=f'File that isnt regularly updated {label}.'
						if is_sys:
								entry["scr"].append(f'{message} and is a system file.')
						else:
							screen = get_delete_patterns(usr, dbtarget)
							if not matches_any_pattern(label, screen):		
								entry["scr"].append(message)		


				if collision_message:
					entry["cerr"].extend(collision_message)


				if entry["cerr"] or entry["flag"] or entry["scr"] or entry["sys"]:
					results.append(entry)

	return results