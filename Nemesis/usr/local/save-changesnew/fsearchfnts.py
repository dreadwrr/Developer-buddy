import hashlib                                                                                                  #11/19/2025

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

#ha funcs
def get_md5(file_path):
    try:
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None 
def calculate_checksum(file_path):
    try:
        hash_func = hashlib.md5()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception:
        return None

# use if path object
def issym(ppath):
    try:
        return ppath.is_symlink()
    except (FileNotFoundError, PermissionError, OSError):
        return False