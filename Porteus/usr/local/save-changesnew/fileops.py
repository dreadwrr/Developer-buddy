import grp
import hashlib
import os
import pwd
import stat
from pathlib import Path
from pyfunctions import epoch_to_date


def find_link_target(file_path, logs):
    target = resolve_target(file_path, logs)
    if target and not os.path.exists(target):
        target = f"broken {target}"
    elif not target:
        logs.append(("DEBUG", f"Symlink target was None : {file_path}"))
        # logging.debug(f"Symlink target was None : {file_path}")
    return target


def find_dir_link_target(dirpath, logger):
    try:
        target = os.readlink(dirpath)
        if target and target.endswith(os.sep):
            base = os.path.dirname(dirpath)
            return os.path.abspath(os.path.join(base, target))
    except OSError as e:
        logger.debug(f"Error checking for broken dir symlinks {dirpath}: {e}")
    return None


def resolve_target(file_path, logs):
    try:
        # absolute = os.path.realpath(file_path)  # 2 method
        target = os.readlink(file_path)
        base = os.path.dirname(file_path)
        absolute = os.path.abspath(os.path.join(base, target))
        return absolute
    except OSError as e:
        logs.append(("DEBUG", f"Error checking symlink target file: {file_path}: {e}"))
        return None


def calculate_checksum(file_path, mtime, mod_time, inode, size_int, logs, prev_hash=None, st=None, retry=1, max_retry=1, cacheable=True):
    total_size = 0
    try:
        hash_func = hashlib.md5()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)
                total_size += len(chunk)

        checks = hash_func.hexdigest()

        if prev_hash is not None:
            if checks == prev_hash:
                return checks, mtime, mod_time, st, "Retried"

        if retry > 0:

            # if not total_size:
            #     logs.append(("DEBUG", f"calculate_checksum Size was zero: {file_path} checksum {checks} and total_size {total_size}"))

            filename = Path(file_path)
            re_st = goahead(filename)
            if re_st == "Nosuchfile":
                return None, mtime, mod_time, st, "Nosuchfile"

            elif re_st:

                a_mod = re_st.st_mtime_ns // 1000

                a_size = re_st.st_size
                a_ino = re_st.st_ino

                if total_size == size_int and mod_time == a_mod and inode and int(inode) == a_ino:
                    status = "Returned"
                    if prev_hash:
                        mtime = epoch_to_date(re_st.st_mtime)
                        status = "Retried"
                    return checks, mtime, mod_time, st, status
                # else:
                #     logs.append(("DEBUG", f"File changed from first stat. the file is Cacheable: {cacheable} doesnt match: {file_path} the follow characteristics: "))
                #     logs.append(("DEBUG", f"Retry #{retry} \\ {max_retry}. Entry mtime {mod_time} size {size_int} inode {inode}"))
                #     logs.append(("DEBUG", f"calculate_checksum checksum size is {total_size} . mtime {a_mod} size {a_size} inode {a_ino}"))
                mtime = epoch_to_date(re_st.st_mtime)
                return calculate_checksum(file_path, mtime, a_mod, a_ino, a_size, logs, checks, re_st, retry=retry - 1, max_retry=max_retry, cacheable=cacheable)

        # logs.append(("DEBUG", f"calculate_checksum returning None: {file_path}"))

        return None, mtime, mod_time, st, "Changed"

    except FileNotFoundError:
        return None, mtime, mod_time, st, "Nosuchfile"
    except PermissionError as e:
        logs.append(("ERROR", f"calculate_checksum Permission denied: {file_path} error: {e}"))
    except Exception as e:
        logs.append(("ERROR", f"Exception calculating checksum for file: {file_path} total_size {total_size} size_int {size_int} error: {e}"))
    return None, mtime, mod_time, st, "Error"


def set_stat(line, file_dt, st, file_us, inode, user, group, mode, symlink, hardlink, logs):

    mtime = file_dt
    mtime_us = file_us
    change_time = st.st_ctime
    ctime = epoch_to_date(change_time)  # .replace(microsecond=0)  # dt obj. convert to str .strftime(fmt)
    size_int = st.st_size
    a_ino = st.st_ino
    if a_ino != int(inode):
        inode = str(st.st_ino)
        try:
            user = pwd.getpwuid(st.st_uid).pw_name
        except KeyError:
            logs.append(("DEBUG", f"set_stat failed to convert uid to user name for user {st.st_uid} line: {line}"))
            user = str(st.st_uid)
        try:
            group = grp.getgrgid(st.st_gid).gr_name
        except KeyError:
            logs.append(("DEBUG", f"set_stat failed to convert gid to group name for group {st.st_gid} line: {line}"))
            group = str(st.st_gid)
        mode = oct(stat.S_IMODE(st.st_mode))[2:]  # '644'
        symlink = "y" if stat.S_ISLNK(st.st_mode) else None
        # symlink = stat.filemode(st.st_mode)  # return '-rw-r--r--' # to match find output %M
        hardlink = st.st_nlink

    return mtime, mtime_us, ctime, inode, size_int, user, group, mode, symlink, hardlink


def truncate_to_6_digits(timestamp):
    return float(f"{timestamp:.6f}")


def goahead(filepath):
    try:
        return filepath.lstat()
    except FileNotFoundError:
        return "Nosuchfile"
    except (OSError):
        pass
        # print(f"Skipping {filepath.name}: {type(e).__name__} - {e}")
    return None


# sym = "y" if os.path.islink(file_path) else None
def updatehlinks(ppath):

    try:
        # except not required but put inplace incase needing to get stat from file
        hardlink = os.stat(ppath, follow_symlinks=False).st_nlink
        return hardlink
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Error while trying to get hardlinks of file {ppath} {e} : {type(e).__name__}")
    return None
