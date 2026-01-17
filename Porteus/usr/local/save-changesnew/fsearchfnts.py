import grp
import hashlib
import logging
import os
import stat
import pwd
from pathlib import Path
from pyfunctions import epoch_to_date
from pyfunctions import goahead
# 01/13/2026


def upt_cache(cfr, checks, file_size, time_stamp, modified_ep, file_path):
    # key = (checks, file_size, modified_ep, file_path)  original when using existing_keys or seen
    if not checks:
        return
    versions = cfr.setdefault(file_path, {})
    row = versions.get(modified_ep)

    if row and row.get("checksum") == checks and row.get("size") == file_size:
        return

    cfr[file_path][modified_ep] = {
        "checksum": checks,
        "size": file_size,
        "modified_time": time_stamp,
    }
    # "owner": str(owner) if owner else '',
    # "domain": str(domain) if domain else ''


def get_cached(cfr, file_size, modified_ep, file_path):
    if not isinstance(cfr, dict):
        return None

    versions = cfr.get(file_path)
    if not versions:
        return None

    if modified_ep is not None:
        row = versions.get(modified_ep)
        if row and file_size == row["size"] and row.get("checksum"):
            return {
                "checksum": row.get("checksum"),
                "modified_ep": modified_ep
            }
            # "user": row.get("owner"),
            # "group": row.get("domain"),

    return None

    # to return the lastest modified_ep
    # valid_eps = [k for k in versions if k not in (None, '')]
    # if not valid_eps:
    #     return None

    # latest_ep = max(valid_eps, key=float)
    # row = versions[latest_ep]
    # if file_size == row["size"]:
    #     return {
    #         "checksum": row.get("checksum"),
    #         "modified_ep": latest_ep
    #     }

    # return None


def truncate_to_6_digits(timestamp):
    return float(f"{timestamp:.6f}")


def calculate_checksum(file_path, mtime, mod_time, inode, size_int, prev_hash=None, st=None, retry=1, cacheable=True):
    total_size = 0

    try:
        hash_func = hashlib.md5()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)
                total_size += len(chunk)

        checks = hash_func.hexdigest()

        if st and checks and prev_hash:
            if checks == prev_hash:
                mtime = epoch_to_date(mod_time)
                logging.debug("Retry #%s calculate_checksum checksum found: %s ", retry, file_path)
                return checks, mtime, st, "Retried"
            else:
                logging.debug("Hash mismatch..  for file: %s - checksum %s and prev_checksum %s", file_path, checks, prev_hash)

        if retry > 0:
            if checks and total_size:
                filename = Path(file_path)
                st = goahead(filename)
                if st == "Nosuchfile":
                    logging.debug("calculate_checksum File no longer exists: %s ", file_path)
                    return None, None, None, "Nosuchfile"

                elif st:
                    a_mod = st.st_mtime
                    a_size = st.st_size
                    a_ino = st.st_ino

                    a_mod = truncate_to_6_digits(a_mod)

                    if not prev_hash:
                        if total_size == size_int and mod_time == a_mod and int(inode) == a_ino:
                            logging.debug("calculate_checksum checksum found matched find: %s ", file_path)
                            return checks, mtime, st, "Returned"
                        else:
                            logging.debug("File changed from find command. the file is Cacheable: %s doesnt match: %s the follow characteristics: ", cacheable, file_path)

                    logging.debug("Retry #%s Entry mtime %s size %s inode %s", retry, mod_time, size_int, inode)
                    logging.debug("calculate_checksum mtime %s size %s inode %s", a_mod, a_size, a_ino)

                    return calculate_checksum(file_path, mtime, a_mod, a_ino, a_size, checks, st, retry=retry - 1, cacheable=cacheable)
            else:
                logging.debug("calculate_checksum Size was zero or unlikely hash failed tried skipping file: %s checksum %s and total_size %s", file_path, checks, total_size)

    except (FileNotFoundError, PermissionError) as e:
        logging.error("calculate_checksum File not found or permission: %s error: %s", file_path, e)
    except Exception as e:
        logging.error("Exception calculating checksum for file: %s total_size %s size_int %s error: %s \n", file_path, total_size, size_int, e, exc_info=True)
        return None, None, None, "Error"
    logging.debug("calculate_checksum returning None: %s", file_path)
    return None, None, None, None


def set_stat(line, file_dt, st, inode, user, group, mode, symlink, hardlink=None):

    mtime = file_dt
    change_time = st.st_ctime
    ctime = epoch_to_date(change_time)  # .replace(microsecond=0)  # dt obj. convert to str .strftime(fmt)
    size_int = st.st_size
    a_ino = st.st_ino
    if a_ino != int(inode):
        inode = str(st.st_ino)
        try:
            user = pwd.getpwuid(st.st_uid).pw_name
        except KeyError:
            logging.debug("set_stat failed to convert uid to user name for line %s:", line)
            user = str(st.st_uid)
        try:
            group = grp.getgrgid(st.st_gid).gr_name
        except KeyError:
            logging.debug("set_stat failed to convert gid to group name for line: %s", line)
            group = str(st.st_gid)
        mode = oct(stat.S_IMODE(st.st_mode))[2:]  # '644'
        symlink = stat.filemode(st.st_mode)  # '-rw-r--r--'
        hardlink = st.st_nlink

    return mtime, ctime, inode, size_int, user, group, mode, symlink, hardlink


# if path object
def issym(ppath):
    try:
        return ppath.is_symlink()
    except (FileNotFoundError, PermissionError, OSError):
        return False


# sym = "y" if os.path.islink(file_path) else None
def updatehlinks(ppath):

    try:
        # except not required but put inplace incase needing to get stat from file
        hardlink = os.stat(ppath, follow_symlinks=False).st_nlink
        return hardlink
    except FileNotFoundError:
        pass
    except Exception as e:
        logging.debug(f"Error while trying to get hardlinks of file {ppath} {e} : {type(e).__name__}")
    return None
