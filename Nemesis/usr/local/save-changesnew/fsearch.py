# Get metadata hash of files and return array 03/25/2026
import logs
import os
from datetime import datetime
from fileops import calculate_checksum
from fileops import find_link_target
from fileops import set_stat
from fsearchfunctions import get_cached
from fsearchfunctions import normalize_timestamp
from logs import emit_log
from pyfunctions import epoch_to_date
from pyfunctions import escf_py

# Find Parallel SORTCOMPLETE search and  ctime hashing


def process_line(line, checksum, file_type, search_start_dt, CACHE_F, logger=None):

    label = "Sortcomplete"
    fmt = "%Y-%m-%d %H:%M:%S"
    CSZE = 1048576

    log_entries = []

    checks = cam = lastmodified = None
    cached = status = None
    target = hardlink = None

    if len(line) < 11:
        emit_log("DEBUG", f"process_line record length less than required 11. skipping: {line}", logs.WORKER_LOG_Q, logger=logger)
        return None, log_entries

    mod_time, access_time, change_time, inode, symlink, hardlink, size, user, group, mode, file_path = line

    escf_path = escf_py(file_path)
    if not os.path.exists(file_path):
        return None, log_entries
    mtime = epoch_to_date(mod_time)
    if not os.path.isfile(file_path):
        if not mtime:
            mt = datetime.now().strftime(fmt)
        else:
            mt = mtime.replace(microsecond=0)
        return ("Nosuchfile", mt, mt, escf_path), log_entries
    ctime = epoch_to_date(change_time)
    if mtime is None:
        return None, log_entries
    if not ctime and file_type == "ctime":
        return None, log_entries
    if not (file_type == "ctime" and ctime is not None and ctime > mtime) and file_type != "main":
        return None, log_entries

    try:
        inode = int(inode)
    except (TypeError, ValueError) as e:
        emit_log("ERROR", f"process_ine from find  {e} {type(e).__name__} inode: {size} line:{line}", logs.WORKER_LOG_Q, logger=logger)
        return None, log_entries
    try:
        size = int(size)
    except (TypeError, ValueError) as e:
        emit_log("ERROR", f"process_line from find  {e} {type(e).__name__} size: {size} line:{line}", logs.WORKER_LOG_Q, logger=logger)
        return None, log_entries

    sym = "y" if isinstance(symlink, str) and symlink.startswith("l") else None

    mtime_us = normalize_timestamp(mod_time)
    if sym != "y" and size and checksum:

        if size > CSZE:
            cached = get_cached(CACHE_F, size, mtime_us, escf_path)
            if cached is None:
                checks, file_dt, file_us, file_st, status = calculate_checksum(file_path, mtime, mtime_us, inode, size, retry=1, max_retry=1, cacheable=True, log_q=logs.WORKER_LOG_Q, logger=logger)
                if checks is not None:
                    if status == "Retried":
                        checks, mtime, st, mtime_us, ctime, inode, size = set_stat(line, checks, file_dt, file_st, file_us, inode, logs.WORKER_LOG_Q, logger=logger)

                    if checks:
                        label = "Cwrite"

                else:
                    if status == "Nosuchfile":
                        mt = mtime.replace(microsecond=0)
                        return ("Deleted", mt, mt, escf_path), log_entries
            else:
                checks = cached.get("checksum")

        else:
            checks, file_dt, file_us, file_st, status = calculate_checksum(file_path, mtime, mtime_us, inode, size, retry=1, max_retry=1, cacheable=False, log_q=logs.WORKER_LOG_Q, logger=logger)
            if checks is not None:
                if status == "Retried":
                    checks, mtime, st, mtime_us, ctime, inode, size = set_stat(line, checks, file_dt, file_st, file_us, inode, logs.WORKER_LOG_Q, logger=logger)

            else:
                if status == "Nosuchfile":
                    mt = mtime.replace(microsecond=0)
                    return ("Deleted", mt, mt, escf_path), log_entries

    elif sym == "y":
        target = find_link_target(file_path, logs.WORKER_LOG_Q, logger=logger)

    if mtime is None:
        emit_log("DEBUG", f"process line no mtime from calculate checksum: {file_path} mtime={mtime}", logs.WORKER_LOG_Q, logger=logger)
        return None, log_entries

    if file_type == "ctime":
        if ctime is None or ctime <= mtime:
            return None, log_entries
        lastmodified = mtime
        mtime = ctime
        cam = "y"
    if mtime < search_start_dt:
        emit_log("DEBUG", f"Warning system cache conflict: {file_path} mtime={mtime} < cutoff={search_start_dt}", logs.WORKER_LOG_Q, logger=logger)
        return None, log_entries

    atime = epoch_to_date(access_time)

    # tuple
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
        lastmodified.strftime(fmt) if lastmodified is not None else None,
        hardlink,
        mtime_us,
        escf_path
    ), log_entries

#
# End parallel #
