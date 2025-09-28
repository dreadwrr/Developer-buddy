# Get metadata hash of files and return array                       09/26/2025
import csv
import hashlib
import multiprocessing
import os
from datetime import datetime
from pyfunctions import epoch_to_date
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
    
def upt_cache(f, inode, size, mtime, checksum, path):
        writer = csv.writer(f, delimiter='|', quoting=csv.QUOTE_MINIMAL)
        writer.writerow([inode, size, mtime, checksum, path])

def get_cached(CACHE_F, inode, size, mtime):
    if not os.path.exists(CACHE_F):
        return None
    with open(CACHE_F, 'r', newline='') as f:
        reader = csv.reader(f, delimiter='|', quoting=csv.QUOTE_MINIMAL)
        for row in reader:
            if len(row) < 5:
                continue
            row_inode, row_size, row_mtime = row[0], row[1], row[2]
            if str(inode) == row_inode and str(size) == row_size and str(mtime) == row_mtime:
                return row[3]  # checksum
    return None


def process_line(line, checksum, type, table, CACHE_F, CSZE):
    fmt = "%Y-%m-%d %H:%M:%S"
    label="Sortcomplete"
    hardlink = None
    cam = None
    sym = None
    cam = None
    checks = None
    hardlink =None
    parts = line.split(maxsplit=9)
    if len(parts) < 9:
        return None

    mod_time, access_time, change_time, inode, size, user, group, mode, file_path = parts[:9]

    mtime = epoch_to_date(mod_time)
    ctime = epoch_to_date(change_time)
    if not os.path.isfile(file_path):
        if not mtime:
            mtime = datetime.now().strftime(fmt)
        return ("Nosuchfile", mtime.replace(microsecond=0), mtime.replace(microsecond=0), file_path)
    if not (type == "ctime" and ctime > mtime) and type != "main": 
        return
    mtime = epoch_to_date(mod_time)
    if mtime is None:
        return

    if table == "sys":
        hardlink = "0"
    
    atime = epoch_to_date(access_time)
    size = int(size)

    if checksum:
        if type == "ctime":
            mtime = ctime
            cam = "y"
        if os.path.islink(file_path):
            sym = "y"

        if size > CSZE:
            checks = get_cached(CACHE_F, inode, size, mod_time)
            if checks is None:
                label="Cwrite"
                checks = calculate_checksum(file_path)
        else:
            checks = calculate_checksum(file_path)

    # tuple 
    return (
        label,
        mtime.replace(microsecond=0),
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

    if cwrite and table not in ('sys', 'watch'):
        with open(CACHE_F, 'a', newline='') as f:
            for res in cwrite:
                epath = escf_py(res[1])
                upt_cache(f, res[2], res[5], res[0].strftime("%Y-%m-%d %H:%M:%S"), res[4], epath)

    return sortcomplete, complete


def process_find_lines(lines, checksum, type, table, CACHE_F, CSZE):
    return process_lines(lines, checksum, type, table, CACHE_F, CSZE)
                                                                                            #
                                                                    #End parallel #    