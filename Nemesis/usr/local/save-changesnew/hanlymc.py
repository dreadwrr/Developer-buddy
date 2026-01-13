
# hybrid analysis  01/09/2025
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from pyfunctions import escf_py
from pyfunctions import epoch_to_date
from pyfunctions import goahead
from pyfunctions import is_integer
from pyfunctions import is_valid_datetime
from pyfunctions import new_meta
from pyfunctions import get_delete_patterns
from pyfunctions import get_recent_changes
from pyfunctions import matches_any_pattern
from pyfunctions import parse_datetime
from pyfunctions import sys_record_flds


def stealth(filename, label, entry, current_size, original_size, cdiag):

    if current_size and original_size:
        file_path = Path(filename)
        if file_path.is_file():
            delta = abs(current_size - original_size)

            if original_size == current_size:
                entry["cerr"].append(f'Warning file {label} same filesize different checksum. Contents changed.')

            elif delta < 12 and delta != 0:
                message = f'Checksum indicates a change in {label}. Size changed slightly - possible stealth edit.'

                if cdiag:
                    entry["scr"].append(f'{message} ({original_size} → {current_size}).')
                else:
                    entry["scr"].append(message)


def hanly(parsed_chunk, checksum, cdiag, dbopt, ps, usr):

    time_period = 5  # days for a file that isnt regularly updated. 5 default

    results = []
    sys_records = []

    fmt = "%Y-%m-%d %H:%M:%S"

    with sqlite3.connect(dbopt) as conn:
        cur = conn.cursor()

        for record in parsed_chunk:

            previous_timestamp = None
            current_size = None
            original_size = None
            is_sys = False

            if len(record) < 15:
                continue

            entry = {"cerr": [], "flag": [], "scr": [], "sys": [], "dcp": []}

            recent_timestamp = parse_datetime(record[0], fmt)
            if not recent_timestamp:
                continue

            filename = record[1]
            label = escf_py(filename)  # human readable

            recent_entries = get_recent_changes(label, cur, 'logs')
            recent_sys = get_recent_changes(label, cur, 'sys', ['count',]) if ps else None

            if not recent_entries and not recent_sys and checksum:
                entry["dcp"].append(record)   # is copy?
                results.append(entry)
                continue

            previous = recent_entries

            if ps and recent_sys and len(recent_sys) > 12:

                previous_timestamp = parse_datetime(recent_sys[0], fmt)

                if previous_timestamp:

                    is_sys = True
                    previous = recent_sys
                    # if doing bulk insert but if one fails wouldnt know not to increment count. currently not using bulk for increment_f
                    # def insert_sys_entry(entry, record, recent_sys, sys_records):
                    #     entry["sys"].append("")
                    #     prev_count = recent_sys[-1]
                    #     sys_record_flds(record, sys_records, prev_count)
                    # previous_sysctime = parse_datetime(recent_sys[2], fmt)
                    # recent_ctime = parse_datetime(record[2], fmt)
                    # if (
                    #     (recent_timestamp > previous_timestamp)
                    #     or (recent_ctime and previous_sysctime and recent_ctime > previous_sysctime)
                    #     or not previous_sysctime
                    # ):
                    #     insert_sys_entry(entry, record, recent_sys, sys_records)
                    # else:
                    #     insert_sys_entry(entry, record, recent_sys, sys_records)
                entry["sys"].append("")
                prev_count = recent_sys[-1]
                sys_record_flds(record, sys_records, prev_count)

            if previous is None or len(previous) < 12:
                continue
            if checksum:
                if not record[5] or not previous[5]:
                    continue
                if not os.path.isfile(filename):
                    entry["flag"].append(f'Deleted {record[0]} {record[0]} {label}')
                    results.append(entry)
                    continue

                current_size = is_integer(record[6])
                original_size = is_integer(previous[6])

            if not is_sys:
                previous_timestamp = parse_datetime(previous[0], fmt)

            if (is_integer(record[3]) is not None and is_integer(previous[3]) is not None  # inode format check
                    and previous_timestamp):
                recent_cam = record[11]
                previous_cam = previous[11]
                cam_file = (recent_cam == "y" or previous_cam == "y")

                mtime_usec_zero = record[14]
                if mtime_usec_zero:
                    # microsecond all zero
                    entry["scr"].append(f'Unusual modified time file has microsecond all zero: {label} at mtime {mtime_usec_zero}')

                if recent_timestamp == previous_timestamp:
                    file_path = Path(filename)

                    if checksum:

                        st = goahead(file_path)
                        if st == "Nosuchfile":
                            entry["flag"].append(f'Deleted {record[0]} {record[0]} {label}')
                            results.append(entry)
                            continue
                        elif st:

                            a_mod = st.st_mtime
                            a_size = st.st_size
                            # a_ino = st.st_ino
                            # auid = pwd.getpwuid(st.st_uid).pw_name
                            # agid = grp.getgrgid(st.st_gid).gr_name
                            # aperm = oct(stat.S_IMODE(st.st_mode))[2:]  # '644'
                            # aperm = stat.filemode(st.st_mode) # '-rw-r--r--'
                            # a_ctime = st.st_ctime
                            # ctime_str = epoch_to_date(a_ctime).replace(microsecond=0)  # dt obj. convert to str .strftime(fmt)
                            # recent_changetime = parse_datetime(record[2])

                            afrm_dt = epoch_to_date(a_mod)
                            if afrm_dt and is_valid_datetime(record[4], fmt):  # access time format check
                                afrm_dt = afrm_dt.replace(microsecond=0)

                                if afrm_dt == previous_timestamp:

                                    if not cam_file:
                                        if record[5] != previous[5]:
                                            entry["flag"].append(f'Suspect {record[0]} {record[2]} {label}')
                                            entry["cerr"].append(f'Suspect file: {label} previous checksum {previous[5]} currently {record[5]}. changed without a new modified time.')

                                    if record[3] == previous[3]:  # inode

                                        metadata = (previous[7], previous[8], previous[9])
                                        if new_meta((record[8], record[9], record[10]), metadata):
                                            entry["flag"].append(f'Metadata {record[0]} {record[2]} {label}')
                                            entry["scr"].append(f'Permissions of file: {label} changed {metadata[0]} {metadata[1]} {metadata[2]} → {record[8]} {record[9]} {record[10]}')

                                else:  # Shifted during search

                                    if not cam_file:
                                        if cdiag:
                                            entry["scr"].append(f'File changed during the search. {label} at {afrm_dt}. Size was {original_size}, now {a_size}')
                                        else:
                                            entry["scr"].append('File changed during search. File likely changed. system cache item.')

                                        # since the modified time changed you could rerun all the checks in the else block below. It would make the function messy with refactoring the below else block. Also these
                                        # files are either system or cache files. Would also lead to repeated feedback when the search is ran again. These checks provide feedback of what files are actively
                                        # changing on the system.

                                        # md5 = None  for detecting Suspicious file. where same mtime different checksum
                                        # if current_size is not None:
                                        #     if current_size > CSZE:
                                        #         md5 =
                                        #     else:
                                        #         md5 = record[5] # file wasnt cached and was calculated in fsearch earlier
                                        # md5 = calculate_checksum(file_path)
                                        # if md5:
                                        #     if md5 != previous[5]:
                                        #         stealth(filename, label, entry, a_size, original_size, cdiag)
                                        # if a_ino == previous[3]:
                                        #     metadata = (previous[7], previous[8], previous[9])
                                        #     if new_meta((auid, agid, aperm), metadata):
                                        #         entry["flag"].append(f'Metadata {record[0]} {record[2]} {label}')
                                        #         entry["scr"].append(f'Permissions of file: {label} changed {metadata[0]} {metadata[1]} {metadata[2]} → {auid} {agid} {aperm}')

                else:

                    if checksum:

                        if record[3] != previous[3]:  # inode

                            if record[5] == previous[5]:

                                entry["flag"].append(f'Overwrite {record[0]} {record[2]} {label}')
                            else:
                                entry["flag"].append(f'Replaced {record[0]} {record[2]} {label}')
                                stealth(filename, label, entry, current_size, original_size, cdiag)

                        else:

                            if record[5] != previous[5]:

                                entry["flag"].append(f'Modified {record[0]} {record[2]} {label}')
                                stealth(filename, label, entry, current_size, original_size, cdiag)
                            else:
                                metadata = (previous[7], previous[8], previous[9])
                                if new_meta((record[8], record[9], record[10]), metadata):
                                    entry["flag"].append(f'Metadata {record[0]} {record[2]} {label}')
                                    entry["scr"].append(f'Permissions of file: {label} changed {metadata[0]} {metadata[1]} {metadata[2]} → {record[8]} {record[9]} {record[10]}')
                                if not cam_file:
                                    entry["flag"].append(f'Touched {record[0]} {record[2]} {label}')

                    else:
                        if record[3] != previous[3]:
                            entry["flag"].append(f'Replaced {record[0]} {record[2]} {label}')
                        else:
                            if not cam_file:
                                entry["flag"].append(f'Modified {record[0]} {record[2]} {label}')

                    if not cam_file:
                        time_delta = datetime.now() - timedelta(days=time_period)
                        if previous_timestamp < time_delta:
                            message = f'File that isnt regularly updated {label}.'
                            if is_sys:
                                entry["scr"].append(f'{message} and is a system file.')
                            else:
                                screen = get_delete_patterns(usr)
                                if not matches_any_pattern(label, screen):
                                    entry["scr"].append(message)
            else:

                print(f"hanlymc timestamp missing or invalid inode format from database for file {filename}\n")
                print("Formatting problem detected")

            if entry["cerr"] or entry["flag"] or entry["scr"] or entry["sys"]:
                results.append(entry)

    return results, sys_records
