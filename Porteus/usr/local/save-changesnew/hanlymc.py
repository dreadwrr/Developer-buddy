
# hybrid analysis  12/07/2025
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from pyfunctions import calculate_checksum
from pyfunctions import collision
from pyfunctions import escf_py
from pyfunctions import getstdate
from pyfunctions import goahead
from pyfunctions import is_integer
from pyfunctions import is_valid_datetime
from pyfunctions import new_meta
from pyfunctions import get_delete_patterns
from pyfunctions import get_recent_changes
from pyfunctions import get_recent_sys
from pyfunctions import matches_any_pattern
from pyfunctions import parse_datetime
from pyfunctions import sys_record_flds

def stealth(filename, label, entry, checksum, current_size, original_size, cdiag, cursor, is_sys):

    collision_message=[]
    if current_size and original_size:
        file_path=Path(filename)
        if file_path.is_file():
            delta= abs(current_size - original_size)
                

            if original_size == current_size:
                entry["cerr"].append(f'Warning file {label} same filesize different checksum. Contents changed.')
            

            elif delta < 12 and delta != 0:
                    message=f'Checksum indicates a change in {label}. Size changed slightly — possible stealth edit.'
                    
                    if cdiag:                                                    
                        entry["scr"].append(f'{message} ({original_size} → {current_size}).')
                    else:
                        entry["scr"].append(message)


            if cdiag:
                    ccheck=collision(label, checksum, current_size, cursor, is_sys)

                    if ccheck:
                        for row in ccheck:
                            b_filename, a_checksum, a_filesize, b_filesize = row
                            collision_message.append(f"COLLISION: {b_filename} | Checksum: {a_checksum} | Sizes: {a_filesize} != {b_filesize}")
						
    return collision_message

def hanly(parsed_chunk, checksum, cdiag, dbopt, ps, usr, dbtarget): 

    results = []
    sys_records = []

    fmt = "%Y-%m-%d %H:%M:%S"
    CSZE = 1024 * 1024

    conn = sqlite3.connect(dbopt)

    with conn:
        cur = conn.cursor()
       

        for record in parsed_chunk:

            if len(record) < 13:
                continue
            is_sys = False
            collision_messages = []
            entry = {"cerr": [], "flag": [], "scr": [], "sys": [], "dcp": []}

            filename = record[1]
            label = escf_py(filename)  # human readable
            
            recent_entries = get_recent_changes(label, cur, 'logs')
            recent_sys = get_recent_sys(label, cur, 'sys', ['count']) if ps else None

            if not recent_entries and not recent_sys:
                entry["dcp"].append(record)   # is copy?
                continue

            filedate = record[0]
            
            recent_timestamp = parse_datetime(filedate, fmt)
            previous = recent_entries
            
            if ps and recent_sys and len(recent_sys) >= 13:
                recent_systime = parse_datetime(recent_sys[0], fmt)
                if recent_systime and recent_systime > recent_timestamp:
                    is_sys = True
                    entry["sys"].append("")
                    prev_count = recent_sys[-1]
                    sys_record_flds(record, sys_records, prev_count)
                    previous = recent_sys

            if previous is None or len(previous) < 11:
                # logging.debug("previous record has unexpected size or is None %s", previous)
                continue

            if checksum:
                if not record[5]:
                    continue

                if is_integer(record[6]): # int(record[6])
                    current_size = int(record[6])
                else:
                    current_size = None

                if is_integer(previous[6]):
                    original_size = int(previous[6]) # int(previous[6])
                else:
                    original_size = None

            else:
                current_size = None
                original_size = None

            previous_timestamp = parse_datetime(previous[0], fmt)

            if (is_integer(record[3]) and is_integer(previous[3]) # format check
                    and recent_timestamp and previous_timestamp):

                if recent_timestamp == previous_timestamp:
                    file_path = Path(filename)

                    if checksum:
                        # in order to catch same mtime and different checksum its required to hash if the mtime changed
                        # so cache cannot be used. if the mtime changed the only way to know is to check and if it
                        # changed rehash the file. So the cache file isnt used but the load is split between hanlymc
                        # and fsearch. that is smaller files < 1MB are hashed in fsearch anything else is hashed here
                        # with the same mtime.


                        if (st := goahead(file_path)):             # we have to verify that the mtime is still the same.
                             
                            if st == "Nosuchfile":
                                entry["flag"].append(f'Deleted {record[0]} {record[2]} {label}')
                            elif st:
                                afrm_dt, afrm_str = getstdate(st, fmt)
                                a_size = st.st_size
                                if afrm_dt and is_valid_datetime(record[3], fmt):

                                    md5 = None
                                    if current_size is not None: 
                                        if current_size > CSZE:
                                            md5 = calculate_checksum(file_path)
                                        else:
                                            md5 = record[5] # file wasnt cached and was calculated in fsearch earlier

                                    if afrm_dt == previous_timestamp:

                                        if  previous[5] and md5 is not None and md5 != previous[5]:
                                            entry["flag"].append(f'Suspect {record[0]} {record[2]} {label}')
                                            entry["cerr"].append(
                                                f'Suspect file: {label} changed without a new modified time.')
                                            
                                        if record[3] == previous[3]:  # inode
                                            metadata = (previous[7], previous[8], previous[9])
                                            if new_meta(record, metadata):
                                            
                                                entry["flag"].append(f'Metadata {record[0]} {record[2]} {label}')
                                                entry["scr"].append(f'Permissions of file: {label} changed {record[8]} {record[9]} {record[10]} → 'f'{metadata[0]} {metadata[1]} {metadata[2]}')
                                        else:

                                            entry["flag"].append(f'Copy {record[0]} {record[2]} {label}')                                               
                                    else:
                                        # shift during search?
                                        if cdiag:
                                            entry["scr"].append(
                                                f'File changed during the search. {label} at {afrm_str}. Size was {original_size}, now {a_size}')
                                        else:
                                            entry["scr"].append(
                                                f'File changed during search. File likely changed. system cache item.')

                else:

                    if checksum:
                        if record[3] != previous[3]:  # inode 
                            
                            if record[5] == previous[5]:
                                

                                entry["flag"].append(f'Overwrite {record[0]} {record[2]} {label}')
                            else:
                                entry["flag"].append(f'Replaced {record[0]} {record[2]} {label}')
                                collision_messages = stealth(filename, label, entry, record[5], current_size, original_size, cdiag, cur, is_sys)
                                
                        else:
                            
                            if record[5] != previous[5]:
                                

                                entry["flag"].append(f'Modified {record[0]} {record[2]} {label}')
                                collision_messages = stealth(filename, label, entry, record[5], current_size, original_size, cdiag, cur, is_sys)
                                
                            else:
                                metadata = (previous[7], previous[8], previous[9])
                                if new_meta(record, metadata):
                                    

                                    entry["flag"].append(f'Metadata {record[0]} {record[2]} {label}')
                                    entry["scr"].append(f'Permissions of file: {label} changed {record[8]} {record[9]} {record[10]} → 'f'{metadata[0]} {metadata[1]} {metadata[2]}')
                                else:
                                    entry["flag"].append(f'Touched {record[0]} {record[2]} {label}')
                                    

                    else:
                        if record[3] != previous[3]:
                            entry["flag"].append(f'Replaced {record[0]} {record[2]} {label}')
                        else:
                            entry["flag"].append(f'Modified {record[0]} {record[2]} {label}')


                    two_days_ago = datetime.now() - timedelta(days=5)
                    if previous_timestamp < two_days_ago:
                        message = f'File that isnt regularly updated {label}.'
                        if is_sys:
                            
                            entry["scr"].append(f'{message} and is a system file.')
                        else:
                            screen = get_delete_patterns(usr, dbtarget)
                            if not matches_any_pattern(label, screen):
                                entry["scr"].append(message)
            else:
             
                print(f"hanlymc timestamp missing or invalid inode format from database for file {filename}\n")
                print("Formatting problem detected")
                #logging.debug(f"current inode {record[3]} previous {previous[3]}, current timestamp {recent_timestamp} previous {previous_timestamp}")
                #logging.debug(f"original {previous} \n current {record}")

            if collision_messages:
                entry["cerr"].extend(collision_messages)

            if entry["cerr"] or entry["flag"] or entry["scr"] or entry["sys"]:
                results.append(entry)

    return results, sys_records
