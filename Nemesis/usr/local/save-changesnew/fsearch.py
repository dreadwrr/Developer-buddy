# Get metadata hash of files and return array 01/13/2026
import logging
import multiprocessing
import os
import traceback
from datetime import datetime
from fsearchfnts import calculate_checksum
from fsearchfnts import get_cached
from fsearchfnts import set_stat
from fsearchfnts import upt_cache
from pyfunctions import epoch_to_date
from pyfunctions import escf_py
from pyfunctions import is_integer
from pyfunctions import setup_logger

fmt = "%Y-%m-%d %H:%M:%S"


# Parallel SORTCOMPLETE search and  ctime hashing
#
def process_line(line, checksum, updatehlinks, file_type, CACHE_F):
    label = "Sortcomplete"
    CSZE = 1048576

    lastmodified = None
    checks = None
    cam = None
    hardlink = None

    if len(line) < 11:
        logging.debug("process_line record length less than required 11. skipping.. record: %s", line)
        return None

    mod_time, access_time, change_time, inode, symlink, hardlink, size, user, group, mode, file_path = line

    escf_path = escf_py(file_path)
    if not os.path.exists(file_path):
        return None
    mtime = epoch_to_date(mod_time)
    if not os.path.isfile(file_path):
        if not mtime:
            mt = datetime.now().strftime(fmt)
        else:
            mt = mtime.replace(microsecond=0)
        return ("Nosuchfile", mt, mt, escf_path)
    ctime = epoch_to_date(change_time)
    if mtime is None:
        return
    if not ctime and file_type == "ctime":
        return
    if not (file_type == "ctime" and ctime is not None and ctime > mtime) and file_type != "main":
        return

    try:
        size_int = is_integer(size)
        if size_int is None:
            size_int = os.path.getsize(file_path)
    except (FileNotFoundError, PermissionError, TypeError, ValueError):
        logging.debug("process_line invalid size skipping..from find parsing: %s, for line: %s", size, line)
        size_int = None

    mtime_epoch = mtime.timestamp()
    if checksum:
        if size_int is not None:
            if size_int > CSZE:
                cached = get_cached(CACHE_F, size_int, mtime_epoch, escf_path)
                if cached is None:
                    checks, file_dt, st, status = calculate_checksum(file_path, mtime, mtime_epoch, inode, size_int, retry=1, cacheable=True)
                    if checks and file_dt:
                        if st:
                            if status == "Retried":
                                if file_type != "ctime":
                                    mtime, ctime, inode, size_int, user, group, mode, symlink, hardlink = set_stat(line, file_dt, st, inode, user, group, mode, symlink, hardlink)

                            label = "Cwrite"
                else:
                    checks = cached.get("checksum")
            else:
                checks, file_dt, st, status = calculate_checksum(file_path, mtime, mtime_epoch, inode, size_int, retry=1, cacheable=False)
                if checks and file_dt:
                    if st:
                        if status == "Retried":
                            if file_type != "ctime":
                                mtime, ctime, inode, size_int, user, group, mode, symlink, hardlink = set_stat(line, file_dt, st, inode, user, group, mode, symlink, hardlink)

    if not updatehlinks:
        hardlink = None
    sym = "y" if isinstance(symlink, str) and symlink.startswith("l") else None

    if file_type == "ctime":
        lastmodified = mtime
        mtime = ctime
        cam = "y"

    atime = epoch_to_date(access_time)

    # satisfy Pyright
    if mtime is None:
        return
    mtime_epoch = mtime.timestamp()
    # tuple
    return (
        label,
        mtime.replace(microsecond=0),
        file_path,
        ctime.strftime(fmt) if ctime is not None else None,
        inode,
        atime.strftime(fmt) if atime is not None else None,
        checks,
        size_int,
        sym,
        user,
        group,
        mode,
        cam,
        lastmodified.strftime(fmt) if lastmodified is not None else None,
        hardlink,
        escf_path,
        mtime_epoch
    )


def process_sys_line(line, checksum):

    label = "Sortcomplete"
    checks = None
    cam = None
    lastmodified = None
    count = 0

    fields = line.split(maxsplit=9)
    if len(fields) < 10:
        logging.debug("process_sys_line record length less than required 10. skipping.. record: %s", line)
        return

    mod_time, access_time, change_time, inode, symlink, size, user, group, mode, file_path = fields

    if not os.path.exists(file_path):
        return None
    mtime = epoch_to_date(mod_time)
    if not os.path.isfile(file_path):
        if not mtime:
            mt = datetime.now().strftime(fmt)
        else:
            mt = mtime.replace(microsecond=0)
        escf_path = escf_py(file_path)
        return ("Nosuchfile", mt, mt, escf_path)
    if mtime is None:
        return

    try:
        size_int = is_integer(size)
        if size_int is None:
            size_int = os.path.getsize(file_path)
    except (FileNotFoundError, PermissionError, TypeError, ValueError):
        logging.debug("process_sys_line invalid size skipping..from find parsing: %s, for line: %s", size, line)
        size_int = None

    ctime = epoch_to_date(change_time)

    mtime_epoch = mtime.timestamp()
    if checksum:
        checks, file_dt, st, status = calculate_checksum(file_path, mtime, mtime_epoch, inode, size_int, retry=1, cacheable=False)
        if checks and file_dt:
            if st:
                if status == "Retried":
                    mtime, ctime, inode, size_int, user, group, mode, symlink, _ = set_stat(line, file_dt, st, inode, user, group, mode, symlink)

    sym = "y" if isinstance(symlink, str) and symlink.startswith("l") else None
    atime = epoch_to_date(access_time)

    return (
        label,
        mtime.replace(microsecond=0),
        file_path,
        ctime.strftime(fmt) if ctime is not None else None,
        inode,
        atime.strftime(fmt) if atime is not None else None,
        checks,
        size_int,
        sym,
        user,
        group,
        mode,
        cam,
        lastmodified,
        count
    )


def process_line_worker(args):
    try:
        chunk, checksum, updatehlinks, file_type, table, process_label, logging_values, CACHE_F = args
    except (ValueError, TypeError) as e:
        print(f"Error process_line_worker. passed args: {args} \nerr: {e} : {type(e).__name__} \n {traceback.format_exc()}")
        return None

    setup_logger(logging_values[1], process_label, logging_values[0])

    t_chunk = len(chunk)

    results = []

    for i, line in enumerate(chunk):
        try:
            if table != "sys":
                result = process_line(line, checksum, updatehlinks, file_type, CACHE_F)
            else:
                result = process_sys_line(line, checksum)
        except Exception as e:
            print(f"process_line_worker - skipping - Error processing line {i} in chunk of {t_chunk - 1}: {e} : {type(e).__name__}")
            logging.error(f"process_line_worker filetype {file_type} table {table} - Error processing line {i} in chunk of {t_chunk - 1}: {e} : {type(e).__name__}", exc_info=True)
            result = None

        if result is not None:
            results.append(result)
    return results


def process_lines(lines, mMODE, checksum, updatehlinks, file_type, table, process_label, logging_values, CACHE_F):

    if len(lines) < 30 or mMODE == "default":
        chunk_args = [(lines, checksum, updatehlinks, file_type, table, process_label, logging_values, CACHE_F)]
        ck_results = [process_line_worker(arg) for arg in chunk_args]
    else:
        min_chunk_size = 10
        max_workers = max(1, min(8, os.cpu_count() or 4, len(lines) // min_chunk_size))

        chunk_size = max(1, (len(lines) + max_workers - 1) // max_workers)
        chunks = [lines[i:i + chunk_size] for i in range(0, len(lines), chunk_size)]

        chunk_args = [(chunk, checksum, updatehlinks, file_type, table, process_label, logging_values, CACHE_F) for chunk in chunks]
        with multiprocessing.Pool(processes=max_workers) as pool:
            ck_results = pool.map(process_line_worker, chunk_args)

    results = [item for sublist in ck_results if sublist is not None for item in sublist]  # flatten the list

    logger = logging.getLogger("FSEARCH")
    sortcomplete = []
    complete = []
    cwrite = []

    for res in results:
        if res is None:
            continue
        if isinstance(res, tuple) and len(res) > 3:
            if res[0] == "Nosuchfile":
                complete.append((res[0], res[1], res[2], res[3]))
            elif res[0] == "Cwrite":
                cwrite.append(res[1:])
                sortcomplete.append(res[1:])
            else:
                sortcomplete.append(res[1:])

    try:
        # existing_keys = set()

        if table != 'sys' and cwrite:

            # for root, versions in CACHE_F.items():
            #     for modified_ep, row in versions.items():
            #         key = (
            #             row.get("checksum"),
            #             row.get("size"),
            #             modified_ep,
            #             root
            #         )
            #         existing_keys.add(key)

            for res in cwrite:
                time_stamp = res[0].strftime("%Y-%m-%d %H:%M:%S")
                # file_path = res[1]
                checks = res[5]
                file_size = res[6]
                # user = res[8]
                # group = res[9]
                epath = res[14]
                mtime_epoch = res[15]

                upt_cache(CACHE_F, checks, file_size, time_stamp, mtime_epoch, epath)

    except Exception as e:
        msg = f'Error updating cache: {type(e).__name__}: {e}'
        print(msg)
        logger.error(msg, exc_info=True)

    return sortcomplete, complete


def process_find_lines(lines, mMODE, checksum, updatehlinks, file_type, table, process_label, logging_values, CACHE_F):
    return process_lines(lines, mMODE, checksum, updatehlinks, file_type, table, process_label, logging_values, CACHE_F)
#
# End parallel #
