
# hybrid analysis  03/02/2025  07/20/2026
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from pyfunctions import clear_conn
from pyfunctions import escf_py
from pyfunctions import is_integer
from pyfunctions import is_valid_datetime
from pyfunctions import new_meta
from pyfunctions import get_delete_patterns
from pyfunctions import get_recent_changes
from pyfunctions import matches_any_pattern
from pyfunctions import parse_datetime
from pyfunctions import sys_record_flds


def target_change(label, entry, recent_sym, previous_sym, link_target, previous_target):
    if recent_sym == "y" and previous_sym == "y":
        if link_target and previous_target and link_target != previous_target:
            entry["scr"].append(f'Symlink target change: {label} {previous_target} → {link_target}')
    elif recent_sym == "y" and not previous_sym:
        entry["cerr"].append(f'Warning file: {label} changed to symlink')
    elif previous_sym == "y" and not recent_sym:
        entry["cerr"].append(f'Warning symlink: {label} changed to file')


def stealth(filename, label, entry, recent_size, previous_size, recent_entropy, previous_entropy, recent_mime_id, previous_mime_id, id_to_mime):

    if recent_size and previous_size:
        file_path = Path(filename)
        if file_path.is_file():
            delta = abs(recent_size - previous_size)

            if previous_size == recent_size:
                entry["cerr"].append(f'Warning file {label} same filesize different checksum. Contents changed.')

            elif delta < 12 and delta != 0:
                entry["scr"].append(f'Checksum indicates a change in {label}. Size changed slightly - possible stealth edit. ({previous_size} → {recent_size}).')

            if recent_mime_id and previous_mime_id and recent_mime_id != previous_mime_id:

                recent_type = id_to_mime.get(recent_mime_id, {}).get("mime")
                previous_type = id_to_mime.get(previous_mime_id, {}).get("mime")

                if recent_type and previous_type:
                    entry["scr"].append(
                        f'File type for file: {label} changed {previous_type} → {recent_type}'
                    )

            if recent_entropy is not None and previous_entropy is not None:

                entropy_delta = abs(recent_entropy - previous_entropy)

                if entropy_delta >= 1.00:
                    entry["cerr"].append(
                        f'Warning high entropy change file: {label} delta {entropy_delta:.2f} ({previous_entropy:.2f} → {recent_entropy:.2f})'
                    )
                elif entropy_delta >= 0.50:
                    entry["scr"].append(
                        f'Entropy delta of .5 or more file: {label} delta {entropy_delta:.2f} ({previous_entropy:.2f} → {recent_entropy:.2f})'
                    )


def hanly(parsed_chunk, checksum, dbopt, ps, usr, id_to_mime):

    time_period = 5  # days for a file that isnt regularly updated. 5 default

    results = []
    sys_records = []

    fmt = "%Y-%m-%d %H:%M:%S"
    csum = False

    conn = sqlite3.connect(dbopt)
    cur = None
    try:
        with conn:
            cur = conn.cursor()

            for record in parsed_chunk:

                previous_timestamp = None
                recent_size = None
                previous_size = None
                is_sys = False

                if len(record) < 18:
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

                if ps and recent_sys and len(recent_sys) > 16:

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
                        prev_count = recent_sys[-1]
                        sys_record_flds(record, sys_records, prev_count)
                    else:
                        print("sys table missing timestamp skipped")
                        continue

                if previous is None or len(previous) < 16:
                    continue

                if checksum:

                    # if not record[5] or not previous[5]:
                    #     continue

                    if not os.path.isfile(filename):
                        entry["flag"].append(f'Deleted {record[0]} {record[0]} {label}')
                        results.append(entry)
                        continue

                    recent_entropy = record[6]
                    previous_entropy = previous[6]
                    recent_mime_id = record[7]
                    previous_mime_id = previous[7]
                    recent_size = record[8]
                    previous_size = previous[8]
                    recent_sym = record[9]
                    previous_sym = previous[9]
                    link_target = record[14]
                    previous_target = previous[14]

                if not is_sys:
                    previous_timestamp = parse_datetime(previous[0], fmt)

                if (is_integer(record[3]) and is_integer(previous[3])
                        and previous_timestamp):  # inode format check
                    recent_cam = record[13]
                    previous_cam = previous[13]
                    cam_file = (recent_cam == "y" or previous_cam == "y")

                    mtime_usec_zero = record[17]
                    if is_integer(mtime_usec_zero) and mtime_usec_zero % 1_000_000 == 0:
                        entry["scr"].append(f'Unusual modified time file has microsecond all zero: {label} at mtime {mtime_usec_zero}')

                    if recent_timestamp == previous_timestamp:
                        if checksum:
                            # file_path = Path(filename)
                            # st = goahead(file_path)
                            # if st == "Nosuchfile":
                            #     entry["flag"].append(f'Deleted {record[0]} {record[0]} {label}')
                            #     results.append(entry)
                            #     continue
                            # elif st:
                            # a_mod = st.st_mtime
                            # afrm_dt = epoch_to_date(a_mod)
                            # a_mod_us = st.st_mtime_ns // 1000
                            # a_size = st.st_size
                            # a_ino = st.st_ino
                            # try:
                            # auid = pwd.getpwuid(st.st_uid).pw_name
                            # except KeyError:
                            # logs.append(("DEBUG", f""hanly failed to convert convert uid to user name for user {st.st_uid} line: {record}"))
                            # auid = str(st.st_uid)
                            # try:
                            # agid = grp.getgrgid(st.st_gid).gr_name
                            # except KeyError:
                            # logs.append(("DEBUG", f""hanly failed to convert gid to group name{st.st_gid} line: {record}"))
                            # agid = str(st.st_gid)
                            # aperm = oct(stat.S_IMODE(st.st_mode))[2:]  # '644'
                            # aperm = stat.filemode(st.st_mode) # '-rw-r--r--'
                            # a_ctime = st.st_ctime
                            # ctime_str = epoch_to_date(a_ctime).replace(microsecond=0)
                            if is_valid_datetime(record[4], fmt):  # access time format check
                                previous_mtime_us = previous[15]
                                if isinstance(previous_mtime_us, int) and mtime_usec_zero == previous_mtime_us:
                                    if not cam_file:
                                        valid_checksums = (record[5] is not None and previous[5] is not None)
                                        if valid_checksums and record[5] != previous[5]:
                                            csum = True
                                            entry["flag"].append(f'Suspect {record[0]} {record[2]} {label}')
                                            entry["cerr"].append(f'Suspect file: {label} previous checksum {previous[5]} currently {record[5]}. changed without a new modified time.')

                                    if record[3] == previous[3]:  # inode

                                        metadata = (previous[10], previous[11], previous[12])
                                        if new_meta((record[10], record[11], record[12]), metadata):
                                            entry["flag"].append(f'Metadata {record[0]} {record[2]} {label}')
                                            entry["scr"].append(f'Permissions of file: {label} changed {metadata[0]} {metadata[1]} {metadata[2]} → {record[10]} {record[11]} {record[12]}')
                                        # else:  # Shifted during search
                                        #     if not cam_file:
                                        #         entry["scr"].append('File changed during search. File likely changed. system cache item.')  # entry["scr"].append(f'File changed during the search. {label} at {afrm_dt}. Size was {previous_size}, now {a_size}')

                                        # since the modified time changed you could rerun all the checks in the else block below. It would make the function messy with refactoring the below else block. Also these
                                        # files are either system or cache files. Would also lead to repeated feedback when the search is ran again. These checks provide feedback of what files are actively
                                        # changing on the system.
                                        # md5 = None  for detecting Suspicious file. where same mtime different checksum
                                        # if recent_size is not None:
                                        #     if recent_size > CSZE:
                                        #         md5 =
                                        #     else:
                                        #         md5 = record[5] # file wasnt cached and was calculated in fsearch earlier
                                        # md5 = calculate_checksum(file_path)
                                        # if md5:
                                        #     if md5 != previous[5]:
                                        #         stealth(filename, label, entry, a_size, previous_size, recent_mime_id, previous_mime_id, id_to_mime)
                                        # if a_ino == previous[3]:
                                        #     metadata = (previous[10], previous[11], previous[12])
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
                                    stealth(filename, label, entry, recent_size, previous_size, recent_entropy, previous_entropy, recent_mime_id, previous_mime_id, id_to_mime)

                                target_change(label, entry, recent_sym, previous_sym, link_target, previous_target)

                            else:

                                if record[5] != previous[5]:

                                    entry["flag"].append(f'Modified {record[0]} {record[2]} {label}')
                                    stealth(filename, label, entry, recent_size, previous_size, recent_entropy, previous_entropy, recent_mime_id, previous_mime_id, id_to_mime)
                                else:

                                    metadata = (previous[10], previous[11], previous[12])
                                    if new_meta((record[10], record[11], record[12]), metadata):
                                        entry["flag"].append(f'Metadata {record[0]} {record[2]} {label}')
                                        entry["scr"].append(f'Permissions of file: {label} changed {metadata[0]} {metadata[1]} {metadata[2]} → {record[10]} {record[11]} {record[12]}')
                                    else:
                                        if not cam_file:
                                            entry["flag"].append(f'Touched {record[0]} {record[2]} {label}')

                                    target_change(label, entry, recent_sym, previous_sym, link_target, previous_target)

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

    finally:
        clear_conn(conn, cur)

    return results, sys_records, csum
