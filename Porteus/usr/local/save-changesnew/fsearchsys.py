# Get metadata hash of files and return array                       03/25/2026
import logs
import os
from datetime import datetime
from fileops import calculate_checksum
from fileops import find_link_target
from fileops import set_stat
from fsearchfunctions import normalize_timestamp
from logs import emit_log
from pyfunctions import epoch_to_date
from pyfunctions import escf_py

# Find Parallel SORTCOMPLETE search and  ctime hashing


def process_sys_line(line, checksum, file_type, search_start_dt, CACHE_F, logger=None):

    label = "Sortcomplete"
    fmt = "%Y-%m-%d %H:%M:%S"
    checks = cam = target = lastmodified = None
    count = 0

    log_entries = []

    if len(line) < 11:
        emit_log("DEBUG", f"process_sys_line record length less than required 11. skipping: {line}", logs.WORKER_LOG_Q, logger=logger)
        return None, log_entries

    mod_time, access_time, change_time, inode, symlink, hardlink, size, user, group, mode, file_path = line

    if not os.path.exists(file_path):
        return None, log_entries
    mtime = epoch_to_date(mod_time)
    if not os.path.isfile(file_path):
        if not mtime:
            mt = datetime.now().strftime(fmt)
        else:
            mt = mtime.replace(microsecond=0)
        escf_path = escf_py(file_path)
        return ("Nosuchfile", mt, mt, escf_path), log_entries
    if mtime is None:
        return None, log_entries

    try:
        inode = int(inode)
    except (TypeError, ValueError) as e:
        emit_log("ERROR", f"process_sys_line from find  {e} {type(e).__name__} inode: {inode} line:{line}", logs.WORKER_LOG_Q, logger=logger)
        return None, log_entries
    try:
        size = int(size)
    except (TypeError, ValueError) as e:
        emit_log("ERROR", f"process_sys_line from find  {e} {type(e).__name__} size: {size} line:{line}", logs.WORKER_LOG_Q, logger=logger)
        return None, log_entries

    ctime = epoch_to_date(change_time)

    sym = "y" if isinstance(symlink, str) and symlink.startswith("l") else None

    mtime_us = normalize_timestamp(mod_time)
    if sym != "y" and checksum:
        checks, file_dt, file_us, file_st, status = calculate_checksum(file_path, mtime, mtime_us, inode, size, retry=2, max_retry=2, cacheable=True, log_q=logs.WORKER_LOG_Q, logger=logger)
        if checks is not None:
            if status == "Retried":
                checks, mtime, st, mtime_us, ctime, inode, size = set_stat(line, checks, file_dt, file_st, file_us, inode, logs.WORKER_LOG_Q, logger=logger)
                if mtime is None:
                    emit_log("ERROR", f"process_sys_line mt was None: line={line}", logs.WORKER_LOG_Q, logger=logger)
                    return None, log_entries

        else:
            if status == "Nosuchfile":
                mt = mtime.replace(microsecond=0)
                escf_path = escf_py(file_path)
                return ("Deleted", mt, mt, escf_path), log_entries

    elif sym == "y":
        target = find_link_target(file_path, logs.WORKER_LOG_Q, logger=logger)

    atime = epoch_to_date(access_time)

    return (
        label,
        mtime.replace(microsecond=0),
        file_path,
        ctime.strftime(fmt) if ctime is not None else None,
        inode,
        atime.strftime(fmt) if atime is not None else None,
        checks,
        size,
        sym,
        user,
        group,
        mode,
        cam,
        target,
        lastmodified,
        count,
        mtime_us
    ), log_entries

#
# End parallel #
