import logs
import os
import traceback
from datetime import datetime
from fileops import calculate_checksum
from fileops import find_link_target
from fileops import set_stat
from fsearchfunctions import get_cached
from fsearchfunctions import normalize_timestamp
from logs import emit_log
from pyfunctions import epoch_to_date
from pyfunctions import escf_py

fmt = "%Y-%m-%d %H:%M:%S"


# Parallel SORTCOMPLETE search and  ctime hashing
#

# Get metadata hash of files and return array 03/02/2026
def process_line(line, checksum, file_type, search_start_dt, CACHE_F):

    label = "Sortcomplete"
    CSZE = 1048576

    log_entries = []

    cached = status = None

    lastmodified = checks = cam = target = hardlink = None

    if len(line) < 11:
        emit_log("DEBUG", f"process_line record length less than required 11. skipping: {line}", logs.WORKER_LOG_Q)
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
        emit_log("ERROR", f"process_ine from find  {e} {type(e).__name__} inode: {size} line:{line}", logs.WORKER_LOG_Q)
        return None, log_entries
    try:
        size = int(size)
    except (TypeError, ValueError) as e:
        emit_log("ERROR", f"process_line from find  {e} {type(e).__name__} size: {size} line:{line}", logs.WORKER_LOG_Q)
        return None, log_entries

    sym = "y" if isinstance(symlink, str) and symlink.startswith("l") else None

    mtime_us = normalize_timestamp(mod_time)
    if sym != "y" and checksum:
        if size > CSZE:
            cached = get_cached(CACHE_F, size, mtime_us, escf_path)
            if cached is None:
                checks, file_dt, file_us, st, status = calculate_checksum(file_path, mtime, mtime_us, inode, size, retry=1, max_retry=1, cacheable=True, logger=logs.WORKER_LOG_Q)
                if checks is not None:
                    if status == "Retried":
                        mtime, mtime_us, ctime, inode, size, user, group, mode, sym, hardlink = set_stat(line, file_dt, st, file_us, inode, user, group, mode, sym, hardlink, logs.WORKER_LOG_Q)
                    label = "Cwrite"
                else:
                    if status == "Nosuchfile":
                        mt = mtime.replace(microsecond=0)
                        return ("Deleted", mt, mt, escf_path), log_entries
            else:
                checks = cached.get("checksum")
        else:
            checks, file_dt, file_us, st, status = calculate_checksum(file_path, mtime, mtime_us, inode, size, retry=1, max_retry=1, cacheable=False, logger=logs.WORKER_LOG_Q)
            if checks is not None:
                if status == "Retried":
                    mtime, mtime_us, ctime, inode, size, user, group, mode, sym, hardlink = set_stat(line, file_dt, st, file_us, inode, user, group, mode, sym, hardlink, logs.WORKER_LOG_Q)
            else:
                if status == "Nosuchfile":
                    mt = mtime.replace(microsecond=0)
                    return ("Deleted", mt, mt, escf_path), log_entries
    elif sym == "y":
        target = find_link_target(file_path, logs.WORKER_LOG_Q)

    atime = epoch_to_date(access_time)

    if mtime is None or (file_type == "main" and mtime < search_start_dt):
        emit_log("DEBUG", f"Warning system cache conflict: {escf_path} mtime={mtime} < cutoff={search_start_dt}", logs.WORKER_LOG_Q)
        return None, log_entries
    if mtime < search_start_dt and label == "Cwrite":
        label = ""
    if file_type == "ctime":
        if ctime and ctime <= mtime:
            return None, log_entries
        lastmodified = mtime
        mtime = ctime
        cam = "y"

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


def process_sys_line(line, checksum):

    label = "Sortcomplete"
    checks = cam = target = lastmodified = None
    count = 0

    log_entries = []

    if len(line) < 11:
        emit_log("DEBUG", f"process_sys_line record length less than required 11. skipping: {line}", logs.WORKER_LOG_Q)
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
        emit_log("ERROR", f"process_sys_line from find  {e} {type(e).__name__} inode: {inode} line:{line}", logs.WORKER_LOG_Q)
        return None, log_entries
    try:
        size = int(size)
    except (TypeError, ValueError) as e:
        emit_log("ERROR", f"process_sys_line from find  {e} {type(e).__name__} size: {size} line:{line}", logs.WORKER_LOG_Q)
        return None, log_entries

    ctime = epoch_to_date(change_time)

    sym = "y" if isinstance(symlink, str) and symlink.startswith("l") else None

    mtime_us = normalize_timestamp(mod_time)
    if sym != "y" and checksum:
        checks, file_dt, file_us, st, status = calculate_checksum(file_path, mtime, mtime_us, inode, size, retry=2, max_retry=2, cacheable=True, logger=logs.WORKER_LOG_Q)
        if checks is not None:
            if status == "Retried":
                mtime, mtime_us, ctime, inode, size, user, group, mode, sym, hardlink = set_stat(line, file_dt, st, file_us, inode, user, group, mode, sym, hardlink, logs.WORKER_LOG_Q)
                if mtime is None:
                    emit_log("ERROR", f"process_sys_line mt was None: line={line}", logs.WORKER_LOG_Q)
                    return None, log_entries
        else:
            if status == "Nosuchfile":
                mt = mtime.replace(microsecond=0)
                escf_path = escf_py(file_path)
                return ("Deleted", mt, mt, escf_path), log_entries
    elif sym == "y":
        target = find_link_target(file_path, logs.WORKER_LOG_Q)

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


def process_line_worker(chunk, checksum, file_type, table, search_start_dt, CACHE_F):

    results = []
    log_entries = []

    for i, line in enumerate(chunk):
        try:
            if table != "sys":
                result, log_ = process_line(line, checksum, file_type, search_start_dt, CACHE_F)
            else:
                result, log_ = process_sys_line(line, checksum)

            if result is not None:
                results.append(result)
            if log_:
                log_entries.extend(log_)

        except Exception as e:
            emit_log("ERROR", f"process_line_worker - Error line {i}: {e}\n{traceback.format_exc()}", logs.WORKER_LOG_Q)

    return results, log_entries
