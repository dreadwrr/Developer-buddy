
# hybrid analysis  9/15/2025
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
from pyfunctions import collision
from pyfunctions import escf_py
from pyfunctions import is_integer
from pyfunctions import is_valid_datetime
from pyfunctions import increment_fname
from pyfunctions import new_meta
from pyfunctions import get_delete_patterns
from pyfunctions import get_md5
from pyfunctions import get_recent_changes
from pyfunctions import matches_any_pattern
from pyfunctions import parse_datetime
collision_message=[]

def stealth(filename, label, entry, checksum, current_size, original_size, cdiag, cursor, is_sys):
	global collision_message
	if current_size and original_size:
		file_path=Path(filename)
		if file_path.is_file():
			delta= abs(current_size - original_size)
				

			if original_size == current_size:
				entry["cerr"].append(f'Warning file {label} same filesize different checksum. Contents changed.')
			

			elif delta < 12 and delta != 0:
					message=f'Checksum indicates a change in {label}. Size changed slightly — possible stealth edit.'
					

					if cdiag == 'true':                                                    
						entry["scr"].append(f'{message} ({original_size} → {current_size}).')
					else:
						entry["scr"].append(message)


			if cdiag == 'true':
					ccheck=collision(label, checksum, current_size, cursor, is_sys)

					if ccheck:
						for row in ccheck:
							b_filename, a_checksum, a_filesize, b_filesize = row
							collision_message.append(f"COLLISION: {b_filename} | Checksum: {a_checksum} | Sizes: {a_filesize} != {b_filesize}")
						

def hanly(parsed_chunk, checksum, cdiag, dbopt, ps, usr, dbtarget):

	global collision_message
	results = []
	fmt = "%Y-%m-%d %H:%M:%S"
	db=False
	conn = sqlite3.connect(dbopt)
	
	with conn:
		cursor = conn.cursor()
		collision_message.clear()
		
		for record in parsed_chunk:
			df=False
			is_sys=False

			if len(record) < 11:
				continue
			entry = {"cerr": [], "flag": [], "scr": [], "sys": [], "dcp": []}
			

			recent_sys = None
			filename = record[1] 
			label = escf_py(filename) # human readable

			
			recent_entries = get_recent_changes(label, cursor, 'logs')

			if ps == 'true':
				recent_sys = get_recent_changes(label, cursor, 'sys')
			
			if not recent_entries and not recent_sys:
				entry["dcp"].append(record)
				continue

			filedate = record[0]
			previous = recent_entries

			if ps == 'true':
				recent_timestamp = parse_datetime(filedate, fmt)
				if recent_sys:
					if recent_sys:
						recent_systime = parse_datetime(recent_sys[0], fmt)
						if recent_systime:
							if recent_systime > recent_timestamp:
								is_sys=True
								increment_fname(cursor, record)
								db=True
								previous = recent_sys #entry["sys"].append(f'{label}')

			if not previous or not filedate or not previous[0] :
				continue
			if checksum == 'true':
				if not record[5] or str(record[5]).strip() == '' or record[5] == 'None':
					continue

				current_size = None
				original_size = None
				if is_integer(record[6]):
					current_size = int(record[6])
					if is_integer(previous[6]):
						original_size = int(previous[6])

			recent_timestamp = parse_datetime(filedate, fmt)
			previous_timestamp = parse_datetime(previous[0], fmt)
			if is_integer(record[3]) and is_integer(previous[3]) and recent_timestamp and previous_timestamp:

				if recent_timestamp == previous_timestamp:

					if checksum == 'true':
						
						if record[5] != previous[5]: # checksum


							entry["flag"].append(f'Suspect {record[0]} {record[2]} {label}')
							entry["cerr"].append(f'Suspect file: {label} changed without a new modified time.')						

						else:

							if record[3] == previous[3]:  # inode
								metadata = (previous[7], previous[8], previous[9])

								if new_meta(record, metadata):


									df=True
									entry["flag"].append(f'Metadata {record[0]} {record[2]} {label}')
									entry["scr"].append(f'Permissions of file: {label} changed {record[8]} {record[9]} {record[10]} → {metadata[0]} {metadata[1]}  {metadata[2] }')
							else:
								df=True
								entry["flag"].append(f'Copy {record[0]} {record[2]} {label}')

						if not df:
							try:
								file_path=Path(filename)
								if file_path.is_file():		
									st = file_path.stat()
									a_size = st.st_size
									a_mod = int(st.st_mtime)
									afrm_str = datetime.utcfromtimestamp(a_mod).strftime(fmt) # actual
									afrm_dt = parse_datetime(afrm_str, fmt)    
									if afrm_dt and is_valid_datetime(record[3], fmt):
										if afrm_dt != previous_timestamp:

											if cdiag == 'true': 
												entry["scr"].append(f'File changed during the search. {label} at {afrm_str}. Size was {original_size}, now {a_size}')
											else:
												entry["scr"].append(f'File changed during search. File likely changed. system cache item.')

											md5=get_md5(file_path)
											if md5:
												if md5 != record[5]:
													stealth(filename, label, entry, md5 , a_size, current_size, cdiag, cursor, is_sys)
											
						
							except Exception as e:
								print(f"Skipping {filename}: {type(e).__name__} - {e}")
								continue


				else:

					if checksum == 'true':


						if record[3] != previous[3]:


							if record[5] == previous[5]:
								entry["flag"].append(f'Overwrite {record[0]} {record[2]} {label}')
							else:
								entry["flag"].append(f'Replaced {record[0]} {record[2]} {label}')
								stealth(filename, label, entry, record[5] ,current_size, original_size, cdiag, cursor, is_sys)

						else:

							if record[5] != previous[5]:
								entry["flag"].append(f'Modified {record[0]} {record[2]} {label}')
								stealth(filename, label, entry, record[5] , current_size, original_size, cdiag, cursor, is_sys)
							else:
								metadata = (previous[7], previous[8], previous[9])

								if new_meta(record, metadata):
									entry["flag"].append(f'Metadata {record[0]} {record[2]} {label}')
									entry["scr"].append(f'Permissions of file: {label} changed {record[8]} {record[9]} {record[10]} → {metadata[0]} {metadata[1]}  {metadata[2] }')
								else:
									entry["flag"].append(f'Touched {record[0]} {record[2]} {label}')

					else:

						if record[3] != previous[3]:
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


		if db:
			conn.commit()
	return results