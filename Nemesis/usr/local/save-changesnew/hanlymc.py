import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from pyfunctions import is_integer
from pyfunctions import is_valid_datetime
from pyfunctions import new_meta
from pyfunctions import get_delete_patterns
from pyfunctions import matches_any_pattern
from pyfunctions import parse_datetime
from pyfunctions import sys_record_flds
from pysql import get_recent_changes
# hybrid analysis original 11/19/2025 updated 02/26/2026


def stealth(filename, label, entry, current_size, original_size, cdiag):

    if current_size and original_size:
        file_path = Path(filename)
        if file_path.is_file():
            delta = abs(current_size - original_size)

            if original_size == current_size:
                entry["cerr"].append(f'Warning file {label} same filesize different checksum. Contents changed.')

            elif delta < 12 and delta != 0:
                message = f'Checksum indicates a change in {label}. Size changed slightly — possible stealth edit.'

                if cdiag:
                    entry["scr"].append(f'{message} ({original_size} → {current_size}).')
                else:
                    entry["scr"].append(message)


def hanly(parsed_chunk, checksum, cdiag, dbopt, ps, usr, logging_values):

    results = []
    sys_records = []
    logs = []
    fmt = "%Y-%m-%d %H:%M:%S"
    csum = False
    time_period = 5  # days for a file that isnt regularly updated. 5 default

    with sqlite3.connect(dbopt) as conn:
        cur = conn.cursor()

        for record in parsed_chunk:

            previous_timestamp = None
            recent_sym = None
            previous_sym = None
            current_size = None
            original_size = None
            is_sys = False

            if len(record) < 17:
                logs.append(("DEBUG", f"sortcomplete entry malformed.  less than required 17 : {record}"))
                continue

            entry = {"cerr": [], "flag": [], "scr": [], "sys": [], "dcp": []}

            recent_timestamp = parse_datetime(record[0], fmt)
            if not recent_timestamp:
                logs.append(("DEBUG", f"missing timestamp on parsed entry: {record}"))
                continue

            filename = record[1]
            label = record[-1]  # human readable

            recent_entries = get_recent_changes(label, cur, 'logs', ['mtime_us'])
            recent_sys = get_recent_changes(label, cur, 'sys', ['mtime_us', 'count']) if ps else None

            if not recent_entries and not recent_sys and checksum:
                entry["dcp"].append(record)  # is copy?
                results.append(entry)
                continue

            previous = recent_entries

            if ps and recent_sys and len(recent_sys) > 14:

                previous_timestamp = parse_datetime(recent_sys[0], fmt)

                if previous_timestamp:

                    is_sys = True
                    previous = recent_sys
                    # if doing bulk insert but if one fails wouldnt know not to increment count. currently not using bulk for increment_f
                    # def insert_sys_entry(entry, record, recent_sys, sys_records):
                    #     prev_count = recent_sys[-1]
                    #     sys_record_flds(record, sys_records, prev_count)
                    # previous_sysctime = parse_datetime(recent_sys[2], fmt)
                    # recent_ctime = parse_datetime(record[2], fmt)
                    # if (
                    #       (recent_timestamp > previous_timestamp)
                    #       or (recent_ctime and previous_sysctime and recent_ctime > previous_sysctime)
                    #       or not (previous_sysctime or previous[5])
                    #       or (record[5] and previous[5] and record[5] != previous[5])
                    # ):
                    #     insert_sys_entry(entry, record, recent_sys, sys_records)
                    prev_count = recent_sys[-1]
                    sys_record_flds(record, sys_records, prev_count)
                else:
                    logs.append(("DEBUG", "sys table missing timestamp skipped"))
                    continue
            elif ps and recent_sys:
                logs.append(("DEBUG", f"recent sys entry less than required length 15 : {recent_sys}"))

            if previous is None or len(previous) < 14:
                logs.append(("DEBUG", f"previous record less than required length 14. previous: {previous}"))
                continue
            if checksum:
                if not record[5] or not previous[5]:
                    continue
                if not os.path.isfile(filename):
                    entry["flag"].append(f'Deleted {record[0]} {record[0]} {label}')
                    results.append(entry)
                    continue

                recent_sym = record[7]
                previous_sym = previous[7]
                current_size = record[6]
                original_size = previous[6]

            if not is_sys:
                previous_timestamp = parse_datetime(previous[0], fmt)

            if (is_integer(record[3]) and is_integer(previous[3])  # format check
                    and previous_timestamp):
                recent_cam = record[11]
                previous_cam = previous[11]
                cam_file = (recent_cam == "y" or previous_cam == "y")

                mtime_usec_zero = record[15]
                if is_integer(mtime_usec_zero) and mtime_usec_zero % 1_000_000 == 0:
                    entry["scr"].append(f'Unusual modified time file has microsecond all zero: {label} timestamp: {mtime_usec_zero}')

                if recent_timestamp == previous_timestamp:
                    if checksum:
                        # st = goahead(file_path)
                        # file_path = Path(filename)
                        # if st == "Nosuchfile":
                        #     entry["flag"].append(f'Deleted {record[0]} {record[0]} {label}')
                        #     results.append(entry)
                        #     continue
                        # elif st:
                        # a_mod = st.st_mtime
                        # a_size = st.st_size
                        # a_ino = st.st_ino
                        # try:
                        # auid = pwd.getpwuid(st.st_uid).pw_name
                        # except KeyError:
                        # logging.debug("hanly failed to convert uid to user name on fstat , record: %s", record)
                        # auid = str(st.st_uid)
                        # try:
                        # agid = grp.getgrgid(st.st_gid).gr_name
                        # except KeyError:
                        # logging.debug("hanly failed to convert gid to group name on fstat , record: %s", record)
                        # agid = str(st.st_gid)
                        # aperm = oct(stat.S_IMODE(st.st_mode))[2:]  # '644'
                        # aperm = stat.filemode(st.st_mode) # '-rw-r--r--'
                        # a_ctime = st.st_ctime
                        # ctime_str = epoch_to_date(a_ctime).replace(microsecond=0)  # dt obj. convert to str .strftime(fmt)
                        # recent_changetime = parse_datetime(record[2])
                        if is_valid_datetime(record[4], fmt):  # access time format check
                            previous_mtime_us = previous[13]
                            if isinstance(previous_mtime_us, int) and mtime_usec_zero == previous_mtime_us:
                                if not cam_file:
                                    if record[5] != previous[5]:
                                        csum = True
                                        entry["flag"].append(f'Suspect {record[0]} {record[2]} {label}')
                                        entry["cerr"].append(f'Suspect file: {label} previous checksum {previous[5]} currently {record[5]}. changed without a new modified time.')

                                if record[3] == previous[3]:  # inode

                                    metadata = (previous[8], previous[9], previous[10])
                                    if new_meta((record[8], record[9], record[10]), metadata):
                                        entry["flag"].append(f'Metadata {record[0]} {record[2]} {label}')
                                        entry["scr"].append(f'Permissions of file: {label} changed {metadata[0]} {metadata[1]} {metadata[2]} → {record[8]} {record[9]} {record[10]}')
                                    # else:  # Shifted during search
                                    #     if not cam_file:
                                    #         if cdiag:
                                    #             entry["scr"].append(f'File changed during the search. {label} at {afrm_dt}. Size was {original_size}, now {a_size}')
                                    #         else:
                                    #             entry["scr"].append('File changed during search. File likely changed. system cache item.')
                                    # since the modified time changed you could rerun all the checks in the else block below. It would make the function messy with refactoring all the checks. Also these
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

                        if record[3] != previous[3]:

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

                                if recent_sym == "y" and previous_sym == "y":
                                    link_target = record[12]
                                    prev_target = previous[12]
                                    if link_target != prev_target:
                                        entry["scr"].append(f'Symlink target change {prev_target} → {link_target}')

                                else:
                                    metadata = (previous[8], previous[9], previous[10])
                                    if new_meta((record[8], record[9], record[10]), metadata):
                                        entry["flag"].append(f'Metadata {record[0]} {record[2]} {label}')
                                        entry["scr"].append(f'Permissions of file: {label} changed {metadata[0]} {metadata[1]} {metadata[2]} → {record[8]} {record[9]} {record[10]}')
                                    else:
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
                print("Hanly formatting problem skipped.")
                logs.append(("DEBUG", f"current inode {record[3]} previous {previous[3]}, current timestamp {recent_timestamp} previous {previous_timestamp} \n original {previous} \n current {record}"))

            if entry["cerr"] or entry["flag"] or entry["scr"] or entry["sys"]:
                results.append(entry)

    return results, sys_records, logs, csum
