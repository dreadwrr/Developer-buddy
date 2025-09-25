# Get metadata hash of files and return array                       09/24/2025
import hashlib
import multiprocessing
import os
from pyfunctions import epoch_to_date
from datetime import datetime

from pyfunctions import escf_py

# Parallel SORTCOMPLETE search and  ctime hashing
#
def calculate_checksum(file_path):
    try:
        hash_func = hashlib.md5()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception:
        return None
    
def upt_cache(CACHE_F, inode, size, mtime, checksum, path):
    with open(CACHE_F, "a") as f:
        f.write(f"{inode}|{size}|{mtime} {checksum} {path}\n")

def get_cached(CACHE_F, inode, size, mtime):
    key = f"{inode}|{size}|{mtime}"
    if not os.path.exists(CACHE_F):
        return None
    with open(CACHE_F, "r") as f:
        for line in f:
            if line.startswith(key + " "):
                parts = line.strip().split(" ", 2)
                if len(parts) >= 2:
                    return parts[1]  # checksum
    return None


def process_line(line, checksum, type, CACHE_F, CSZE):
    fmt = "%Y-%m-%d %H:%M:%S"
    hardlink = None
    cam = ""
    sym = ""
    cam = ""
    checks = ""
    parts = line.split(maxsplit=9)
    if len(parts) < 9:
        return None

    mod_time, access_time, change_time, inode, size, user, group, mode, file_path = parts[:9]

    mod_time = int(mod_time)
    change_time = int(change_time)
    if not (type == "ctime" and change_time > mod_time) and type != "main": 
        return
    mtime = epoch_to_date(mod_time)
    if mtime is None:
        return
    
    size = int(size)

    if not os.path.exists(file_path):
        now_str = datetime.now().strftime(fmt)
        return ("Nosuchfile", now_str, now_str, file_path)

    if checksum:
        if size > CSZE:
            checks = get_cached(CACHE_F, inode, size, mod_time)
            if checks is None:
                checks = calculate_checksum(file_path)
                upt_cache(CACHE_F, inode, size, mod_time, checks, file_path)
        else:
            checks = calculate_checksum(file_path)

    mtime = epoch_to_date(mod_time)
    atime = epoch_to_date(access_time)
    ctime = epoch_to_date(change_time)

    if type == "ctime":
        mtime = ctime
        cam = "y"

    if os.path.islink(file_path):
        sym = "y"

    # Return tuple with all metadata
    return (
        mtime,
        file_path,
        ctime.strftime(fmt),
        inode,
        atime.strftime(fmt),
        checks,
        str(size),
        sym,
        user,
        group,
        mode,
        cam,
        hardlink
    )


def process_line_worker(args):
    line, checksum, type, CACHE_F, CSZE = args
    return process_line(line, checksum, type, CACHE_F, CSZE)


def process_lines(lines, checksum, type, CACHE_F, CSZE):
    args = [(line, checksum, type, CACHE_F, CSZE) for line in lines]

    if len(lines) < 100:
        results = [process_line_worker(arg) for arg in args]
    else:
        with multiprocessing.Pool() as pool:
            results = pool.map(process_line_worker, args)

    sortcomplete = []
    complete = []

    for res in results:
        if res is None:
            continue
        if isinstance(res, tuple) and len(res) > 0 and res[0] == "Nosuchfile":
      
            epath = escf_py(res[3]) if len(res) > 3 else ""
            # Append tuple with escaped path
            complete.append((res[0], res[1], res[2], epath))
        else:
            sortcomplete.append(res)

    return sortcomplete, complete


def process_find_lines(lines, checksum, type, CACHE_F, CSZE):
    return process_lines(lines, checksum, type, CACHE_F, CSZE)
                                                                                            #
                                                                    #End parallel #    