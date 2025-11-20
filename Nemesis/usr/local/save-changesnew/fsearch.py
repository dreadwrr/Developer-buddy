# Get metadata hash of files and return array                       11/19/2025
import multiprocessing
import traceback
import os
from datetime import datetime
from fsearchfnts import calculate_checksum
from fsearchfnts import get_cached
#from fsearchfnts import issym
from fsearchfnts import upt_cache
from pyfunctions import epoch_to_date
from pyfunctions import escf_py
from pyfunctions import is_integer
from pyfunctions import unescf_py

fmt = "%Y-%m-%d %H:%M:%S"

# Parallel SORTCOMPLETE search and  ctime hashing
#
def process_line(line, checksum, updatehlinks, file_type, CACHE_F):
    label="Sortcomplete"
    CSZE = 1024 * 1024
    lastmodified = None
    checks = None
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
    if not os.path.isfile(file_name):
        if not mtime:
            mt = datetime.now().strftime(fmt)
        else:
            mt = mtime.replace(microsecond=0)
        return ("Nosuchfile", mt, mt, escf_path)
    ctime = epoch_to_date(change_time)
    if not ctime and file_type == "ctime":
        return
    if not (file_type == "ctime" and ctime > mtime) and file_type != "main": 
        return
    if mtime is None:
        return
    try:
        if is_integer(size):
            size_int = int(size)
        else:
            size_int = os.path.getsize(file_name)
    except (FileNotFoundError, PermissionError, TypeError, ValueError):
        size_int = None

    if checksum:
        if size_int is not None and size_int > CSZE:
            checks = get_cached(CACHE_F, size, mod_time, escf_path)
            if checks is None:
                label="Cwrite"
                checks = calculate_checksum(file_name)
        else:
            checks = calculate_checksum(file_name)

    if updatehlinks:
        try:
            # except not required but put inplace incase needing to get stat from file
            hardlink = os.stat(file_name, follow_symlinks=False).st_nlink 
        except FileNotFoundError as e:
            hardlink = None
        except Exception as e:
            print(f"Error while trying to get hardlinks of file {file_name} {e} : {type(e).__name__}")

    hardlink = hardlink - 1 if hardlink else None

    sym = "y" if os.path.islink(file_name) else None

    if file_type == "ctime":
        lastmodified = mtime
        mtime = ctime
        cam = "y"
    
    atime = epoch_to_date(access_time)

    # tuple 
    return (

        label,
        mtime.replace(microsecond=0),
        file_name,
        ctime.strftime(fmt) if ctime is not None else None,
        inode,
        atime.strftime(fmt) if atime is not None else None,
        checks,
        str(size_int),
        sym,
        user,
        group,
        mode,
        cam,
        lastmodified.strftime(fmt) if lastmodified is not None else None,
        str(hardlink),
        escf_path
    )

def process_sys_line(line, checksum):

    label="Sortcomplete"

    lastmodified = None
    cam = None
    lastmodified = None
    cval = "0"
    parts = line.split(maxsplit=8)
    if len(parts) < 9:
        return None

    mod_time, access_time, change_time, inode, size, user, group, mode, escf_path = parts

    file_name = unescf_py(escf_path)
    if not os.path.exists(file_name):
        return None
    mtime = epoch_to_date(mod_time)
    if not os.path.isfile(file_name):
        if not mtime:
            mt = datetime.now().strftime(fmt)
        else:
            mt = mtime.replace(microsecond=0)
        return ("Nosuchfile", mt, mt, escf_path)
    if mtime is None:
        return
    checks = None
    if checksum:
        checks = calculate_checksum(file_name)
    sym = "y" if os.path.islink(file_name) else None   
    try:
        if is_integer(size):
            size_int = int(size)
        else:
            size_int = os.path.getsize(file_name)
    except (FileNotFoundError, PermissionError, TypeError, ValueError):
        size_int = None
    ctime = epoch_to_date(change_time)    
    atime = epoch_to_date(access_time)

    # tuple 
    return (
        label,
        mtime.replace(microsecond=0),
        file_name,
        ctime.strftime(fmt) if ctime is not None else None,
        inode,
        atime.strftime(fmt) if atime is not None else None,
        checks,
        str(size_int),
        sym,
        user,
        group,
        mode,
        cam,
        lastmodified,
        str(cval),
        escf_path
    )

def process_line_worker(args):
    try:
        chunk, checksum, updatehlinks, file_type, table, CACHE_F = args
    except (ValueError, Exception) as e: 
        ems = f"Error processing line in process_line_worker: {e} : {type(e).__name__}"
        print(ems)
        #logging.error(f"{ems} {e}", exc_info=True)
        return None
            
    t_chunk = len(chunk)

    results = []

    for i, line in enumerate(chunk):
        try:
            if table != "sys":
                result = process_line(line, checksum, updatehlinks, file_type, CACHE_F)
            else:
                result = process_sys_line(line, checksum)
        except Exception as e:
            ems = f"process_line_worker filetype {file_type} table {table} - Error processing line {i} in chunk of {t_chunk - 1}: {e} : {type(e).__name__} \n {traceback.format_exc()}"
            print(ems)
            #logging.error(f"process_line_worker Error processing line {i} in chunk {chunk_index}: {e}", exc_info=True)
            result = None

        if result is not None:
            results.append(result)
    return results


def process_lines(lines, checksum, updatehlinks, file_type, table, CACHE_F):


    if len(lines) < 30:
        chunk_args = [(lines, checksum, updatehlinks, file_type, table, CACHE_F)]
        ck_results = [process_line_worker(arg) for arg in chunk_args]
    else:
        max_workers = max(1, min(8, os.cpu_count() or 4, len(lines)))

        chunk_size = max(1, (len(lines) + max_workers - 1) // max_workers)
        chunks = [lines[i:i + chunk_size] for i in range(0, len(lines), chunk_size)]

        chunk_args = [(chunk, checksum, updatehlinks, file_type, table, CACHE_F) for chunk in chunks]
        with multiprocessing.Pool(processes=max_workers) as pool:
            ck_results = pool.map(process_line_worker, chunk_args)

    results = [item for sublist in ck_results if sublist is not None for item in sublist] # flatten the list

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


def process_find_lines(lines, checksum, updatehlinks, file_type, table, CACHE_F):
    return process_lines(lines, checksum, updatehlinks, file_type, table, CACHE_F)
                                                                                            #
                                                                    #End parallel #