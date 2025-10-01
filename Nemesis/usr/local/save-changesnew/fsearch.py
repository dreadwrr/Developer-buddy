# Get metadata hash of files and return array                       09/30/2025
import hashlib
import multiprocessing
import os
from datetime import datetime
from pyfunctions import epoch_to_date
from pyfunctions import escf_py
from pyfunctions import unescf_py


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
    

def upt_cache(cfr, existing_keys, size, mtime, checksum, path):
    key = (checksum, str(size), str(mtime), path)
    if key not in existing_keys:
        entry = {
            "checksum": checksum,
            "size": str(size),
            "mtime": str(mtime),
            "path": path
        }
        cfr.append(entry)
        existing_keys.add(key)


def get_cached(cfr, size, mtime, path):
    if not cfr:
        return None

    for row in cfr:
        if not all(key in row for key in ("size", "mtime", "path", "checksum")):
            continue
        if str(size) == row["size"] and str(mtime) == row["mtime"] and path == row["path"]:
            return row["checksum"]
    
    return None


def process_line(line, checksum, type, table, CACHE_F, CSZE):
    fmt = "%Y-%m-%d %H:%M:%S"
    label="Sortcomplete"
    lastmodified = None
    checks = None
    sym = None
    cam = None
    hardlink =None
    parts = line.split(maxsplit=8)
    if len(parts) < 9:
        return None

    mod_time, access_time, change_time, inode, size, user, group, mode, escf_path = parts

    file_name = unescf_py(escf_path)
    if not os.path.exists(file_name):
        return None

    mtime = epoch_to_date(mod_time)
    ctime = epoch_to_date(change_time)

    if not os.path.isfile(file_name):
        if not mtime:
            mtime = datetime.now().strftime(fmt)
        return ("Nosuchfile", mtime.replace(microsecond=0), mtime.replace(microsecond=0), escf_path)
    if not (type == "ctime" and ctime > mtime) and type != "main": 
        return
    if mtime is None:
        return

    if table == "sys":
        hardlink = "0"
    
    atime = epoch_to_date(access_time)

    try:
        size_int = int(size)
    except (TypeError, ValueError):
        size_int = None

    if checksum:
        if type == "ctime":
            lastmodified = mtime
            mtime = ctime
            cam = "y"
        if os.path.islink(file_name):
            sym = "y"

        if size_int is not None and size_int > CSZE:
            checks = get_cached(CACHE_F, size, mod_time, escf_path)
            if checks is None:
                label="Cwrite"
                checks = calculate_checksum(file_name)
        else:
            checks = calculate_checksum(file_name)

    # tuple 
    return (
        label,
        mtime.replace(microsecond=0),
        file_name,
        ctime.strftime(fmt),
        inode,
        atime.strftime(fmt),
        checks,
        str(size_int),
        sym,
        user,
        group,
        mode,
        cam,
        lastmodified.strftime(fmt) if lastmodified is not None else None,
        hardlink,
        escf_path
    )

def process_line_worker(args):
    line, checksum, type, table, CACHE_F, CSZE = args
    return process_line(line, checksum, type, table, CACHE_F, CSZE)


def process_lines(lines, checksum, type, table, CACHE_F, CSZE):
    args = [(line, checksum, type, table, CACHE_F, CSZE) for line in lines]

    if len(lines) < 100:
        results = [process_line_worker(arg) for arg in args]
    else:
        with multiprocessing.Pool(processes=os.cpu_count() or 4) as pool:
            results = pool.map(process_line_worker, args)

    sortcomplete = []
    complete = []
    cwrite = []

    for res in results:
        if res is None:
            continue
        if isinstance(res, tuple) and len(res) > 0: 
            if res[0] == "Nosuchfile":
      
                epath = escf_py(res[3]) if len(res) > 3 else ""

                complete.append((res[0], res[1], res[2], epath))

            elif res[0] == "Cwrite":
                cwrite.append(res[1:])
                sortcomplete.append(res[1:])
            else:
                sortcomplete.append(res[1:])

    existing_keys = set()

    if cwrite and table not in ('sys', 'watch'):
        
        if CACHE_F:
            for row in CACHE_F:
                key = (row["checksum"], row["size"], row["mtime"], row["path"])
                existing_keys.add(key)

        for res in cwrite:
            epath = res[14]
            upt_cache(CACHE_F, existing_keys, res[6], res[0].strftime("%Y-%m-%d %H:%M:%S"), res[5], epath) 

    return sortcomplete, complete


def process_find_lines(lines, checksum, type, table, CACHE_F, CSZE):
    return process_lines(lines, checksum, type, table, CACHE_F, CSZE)
                                                                                            #
                                                                    #End parallel #    