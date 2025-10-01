# hybrid analysis efficient table queries refined developer buddy  09/15/2025
import pyfunctions
from datetime import datetime, timedelta
from pathlib import Path

def stealth(filename, label, cer, scr, collision_message, checksum, current_size, original_size, cdiag, cursor):
		
	if current_size and original_size:

		file_path=Path(filename)
		if file_path.is_file():
			delta= abs(current_size - original_size)
				
			if original_size == current_size:  # flag ***
				print(f'Warning file {label} same filesize different checksum. Contents changed.', file=cer)

			elif delta < 12 and delta != 0:  # stealth cng?
				message=f'Checksum indicates a change in {label}. Size changed slightly — possible stealth edit.'
				
				if cdiag == 'true':
					print(f'{message} ({original_size} → {current_size}).', file=scr)
				else:
					print(f'{message}', file=scr)

			if cdiag == 'true':
				ccheck=pyfunctions.collision(label, checksum, current_size, cursor, 'logs')
				if ccheck:
					for row in ccheck:
						b_filename, a_checksum, a_filesize, b_filesize = row
						message=f"COLLISION: {b_filename} | Checksum: {a_checksum} | Sizes: {a_filesize} != {b_filesize}"
						collision_message.append(message)



#Hybrid analysis
def hanly(parsed, recorddata, checksum, cdiag, conn, c, ps, usr, dbtarget, file, file2, file3, file4):

	fmt = "%Y-%m-%d %H:%M:%S"
	collision_message=[]
	db=False
	for record in parsed:
		df=False
		is_sys=False

		filename = record[1] 
		label = pyfunctions.escf_py(filename) # human readable

		recent_entries = pyfunctions.get_recent_changes(label, c, 'logs')
		recent_sys = pyfunctions.get_recent_changes(label, c, 'sys') if ps else None
		
		if not recent_entries and not recent_sys:
			recorddata.append(record) # is copy?
			continue

		filedate = record[0]
		previous = recent_entries
		recent_timestamp = pyfunctions.parse_datetime(filedate, fmt)

		if ps == 'true' and recent_sys and len(recent_sys) > 0:  # check sys	
			recent_systime = pyfunctions.parse_datetime(recent_sys[0], fmt)
			if recent_systime and recent_systime > recent_timestamp:
				is_sys=True
				db=True
				pyfunctions.increment_fname(c, record) # add to system file count db
				previous = recent_sys

		if not previous or not filedate or not previous[0]:
			continue
		if checksum == 'true':
			if not record[5] or record[5] == 'None' or not previous[5] or previous[5] == 'None' or len(record) < 13: # checksum
				continue
			current_size = int(record[6]) if pyfunctions.is_integer(record[6]) else None
			original_size = int(previous[6]) if pyfunctions.is_integer(previous[6]) else None
		else:
			current_size = None
			original_size = None
						
		previous_timestamp = pyfunctions.parse_datetime(previous[0], fmt)

		if pyfunctions.is_integer(record[3]) and pyfunctions.is_integer(previous[3]) and recent_timestamp and previous_timestamp:

			if recent_timestamp == previous_timestamp: # Not modified?
				file_path = Path(filename)

				if checksum == 'true':
					if record[5] != previous[5]: # checksum, filesize
						if file_path.is_file():
							if (st := pyfunctions.goahead(file_path)):
								afrm_dt, _= pyfunctions.getstdate(st, fmt)
								if afrm_dt and pyfunctions.is_valid_datetime(record[3], fmt):
									if afrm_dt == previous_timestamp:

										md5 = pyfunctions.get_md5(file_path)
										if md5 and md5 != previous[5]:


											pyfunctions.log_event("Suspect", record, label, file, file2) # Flag *** 
											print(f'Suspect file: {label} changed without a new modified time.', file3) 
						else:
							pyfunctions.log_event("Deleted", record, label, file, file2)

					else:
						if record[3] == previous[3]:  # inode
							metadata = (previous[7], previous[8], previous[9])
							if pyfunctions.new_meta(record, metadata):


								df=True
								pyfunctions.log_event("Metadata", record, label, file, file2)
								print(f'Permissions of file: {label} changed {record[8]} {record[9]} {record[10]} → {metadata[0]} {metadata[1]}  {metadata[2] }', file4)
						else: 
							df=True
							pyfunctions.log_event("Copy", record, label, file, file2) # inode change preserved meta


                        # shift during search?
						if not df and file_path.is_file():
							if (st := pyfunctions.goahead(file_path)):
								afrm_dt, afrm_str = pyfunctions.getstdate(st, fmt)
								if afrm_dt and pyfunctions.is_valid_datetime(record[3], fmt):
									if afrm_dt != previous_timestamp:
										a_size = st.st_size


										if cdiag == 'true': 
											print(f'File changed during the search. {label} at {afrm_str}. Size was {original_size}, now {a_size} ', file=file4)
										else:
											print(f'File changed during search. File likely changed. system cache item.', file=file4)

						elif not df:
							pyfunctions.log_event("Deleted", record, label, file, file2)


			else: # Modified.

				if checksum == 'true':
					if record[3] != previous[3]: # Inode

						if record[5] == previous[5]:


							pyfunctions.log_event("Overwrite", record, label, file, file2)
						else:
							pyfunctions.log_event("Replaced", record, label, file, file2)
							stealth(filename, label, file3, file4, collision_message, record[5] ,current_size, original_size, cdiag, c) # Flag *** ?
							
					else:

						if record[5] != previous[5]:


							pyfunctions.log_event("Modified", record, label, file, file2)
							stealth(filename, label, file3, file4, collision_message, record[5] , current_size, original_size, cdiag, c)  # Flag *** ?

						else:			
							metadata = (previous[7], previous[8], previous[9])
							if pyfunctions.new_meta(record, metadata):


								pyfunctions.log_event("Metadata", record, label, file, file2)
								print(f'Permissions of file: {label} changed {record[8]} {record[9]} {record[10]} → {metadata[0]} {metadata[1]}  {metadata[2] }', file4)
							else:
								pyfunctions.log_event("Touched", record, label, file, file2)


				else:
					if record[3] != previous[3]:
						pyfunctions.log_event("Replaced", record, label, file, file2)
					else: 
						pyfunctions.log_event("Modified", record, label, file, file2)

					
				two_days_ago = datetime.now() - timedelta(days=2)
				if previous_timestamp < two_days_ago:
					message=f'File that isnt regularly updated {label}.'
					if is_sys:
						print(f'{message} and is a system file.', file=file4)
					else:
						screen = pyfunctions.get_delete_patterns(usr, dbtarget)
						if not pyfunctions.matches_any_pattern(label, screen):		
							print(f'{message}.', file=file4)


	if db:
		conn.commit()
	if collision_message:
		for entry in collision_message:
			print(entry, file=file3)


# try: 
# 	# if label.find("\\") == -1: skip   # str.encode().decode('unicode_escape') 
# 	filename=codecs.decode(label, 'unicode_escape')
# 	if not filename:
# 		raise ValueError("Empty filename")
# except Exception as e:
# 	print(f"Skipping label due to decode file: {label} error: {e}")
# 	continue
