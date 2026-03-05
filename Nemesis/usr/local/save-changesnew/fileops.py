import grp
import hashlib
import os
import pwd
import stat
from logs import emit_log
from pathlib import Path
from pyfunctions import epoch_to_date


def find_link_target(file_path, logger=None):
    target = resolve_target(file_path, logger)
    if target and not os.path.exists(target):
        target = f"broken {target}"
    elif not target:
        emit_log("DEBUG", f"Symlink target was None : {file_path}", logger)
    return target


def resolve_target(file_path, logger=None):
    try:
        # absolute = os.path.realpath(file_path)  # 2 method
        target = os.readlink(file_path)
        base = os.path.dirname(file_path)
        absolute = os.path.abspath(os.path.join(base, target))
        return absolute
    except OSError as e:
        emit_log("DEBUG", f"Error checking symlink target file: {file_path}: {e}", logger)
        return None


def find_dir_link_target(dirpath, logger=None):
    try:
        target = os.readlink(dirpath)
        if target and target.endswith(os.sep):
            base = os.path.dirname(dirpath)
            return os.path.abspath(os.path.join(base, target))
    except OSError as e:
        emit_log("DEBUG", f"Error checking for broken dir symlinks {dirpath}: {e}", logger)
    return None


def calculate_checksum(file_path, mtime, mod_time, inode, size_int, prev_hash=None, st=None, retry=1, max_retry=1, cacheable=True, logger=None):
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
            #     emit_log("DEBUG", f"calculate_checksum Size was zero: {file_path} checksum {checks} and total_size {total_size}"), logger)

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
                #     emit_log("DEBUG", f"File changed from first stat. the file is Cacheable: {cacheable} doesnt match: {file_path} the follow characteristics: "), logger)
                #     emit_log("DEBUG", f"Retry #{retry} \\ {max_retry}. Entry mtime {mod_time} size {size_int} inode {inode}"), logger)
                #     emit_log("DEBUG", f"calculate_checksum checksum size is {total_size} . mtime {a_mod} size {a_size} inode {a_ino}"), logger)
                mtime = epoch_to_date(re_st.st_mtime)
                return calculate_checksum(file_path, mtime, a_mod, a_ino, a_size, checks, re_st, retry=retry - 1, max_retry=max_retry, cacheable=cacheable, logger=logger)

        # emit_log("DEBUG", f"calculate_checksum returning None: {file_path}"), logger)

        return None, mtime, mod_time, st, "Changed"

    except FileNotFoundError:
        return None, mtime, mod_time, st, "Nosuchfile"
    except PermissionError as e:
        emit_log("ERROR", f"calculate_checksum Permission denied: {file_path} error: {e}", logger)
    except Exception as e:
        emit_log("ERROR", f"Exception calculating checksum for file: {file_path} total_size {total_size} size_int {size_int} error: {e}", logger)
    return None, mtime, mod_time, st, "Error"


def set_stat(line, file_dt, st, file_us, inode, user, group, mode, symlink, hardlink, logger=None):

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
            emit_log("DEBUG", f"set_stat failed to convert uid to user name for user {st.st_uid} line: {line}", logger)
            user = str(st.st_uid)
        try:
            group = grp.getgrgid(st.st_gid).gr_name
        except KeyError:
            emit_log("DEBUG", f"set_stat failed to convert gid to group name for group {st.st_gid} line: {line}", logger)
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
