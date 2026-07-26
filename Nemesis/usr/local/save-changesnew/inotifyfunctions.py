import logging
import os
import re
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path
from fsearchfunctions import upt_cache
from pyfunctions import ap_decode
from pyfunctions import epoch_to_date
from pyfunctions import escf_py
from pyfunctions import parse_datetime
from rntchangesfunctions import removefile
# 07/25/2026


# Globals
QUOTED_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')

# xRC functions


def process_status(pattern):
    """ return True if process is running """
    try:
        result = subprocess.run(
            ["pgrep", "-af", pattern],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception as e:
        logging.error(f"process_status xRC failed to check if process was running: {e} {type(e).__name__}", exc_info=True)
    return False


def process_by_target(target):
    """ return process id """
    try:
        result = subprocess.run(
            ["pgrep", "-f", target],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True
        )
    except OSError as e:
        logging.error(f"process_status failed to check if process was running: {e} {type(e).__name__}", exc_info=True)
        return 0

    if result.returncode != 0:
        return 0
    return int(result.stdout.split()[0])


def _fk_process(pattern):
    """ close process by pattern """
    try:
        result = subprocess.run(
            ["pkill", "-f", pattern],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception as e:
        logging.error(f"_fk_process xRC failure to close process. err: {e} {type(e).__name__} \n", exc_info=True)
    return False


def drop_pid(pid, pid_file=None):
    """ formerly shutdown. close process by id """
    try:
        os.kill(-pid, signal.SIGTERM)
        if pid_file:
            removefile(pid_file)
        return True
    except ProcessLookupError:
        pass  # already gone
    except PermissionError:
        print("shutdown func inotifywait permission error")


def get_pid(pid_file):
    """ not used as could accidently kill the wrong process """
    pid = None
    if os.path.isfile(pid_file):
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
        except (ValueError, OSError):
            return None
    return pid


# cross platform
# def process_kill(pid, pid_file=None):
#     try:
#         proc = psutil.Process(pid)
#         proc.terminate()
#         proc.wait(timeout=5)
#         removefile(pid_file)
#         return True
#     except psutil.TimeoutExpired:
#         proc.kill()
#         proc.wait()
#         removefile(pid_file)
#         return True
#     except psutil.NoSuchProcess:
#         return False
#     except psutil.AccessDenied:
#         return False
# end cross platform


def old_pid_check(pid_file, new_pid, logger):
    """ if there is an old pid file try to kill.
         Returns False if there was but was unable to close process """
    res = True

    if os.path.isfile(pid_file):
        with open(pid_file) as f:
            parts = f.read().rstrip("\n").split("|", 1)

        if parts and len(parts) == 2:
            stored_pid, stored_start = parts
            stored_pid = int(stored_pid)
            differs = new_pid and new_pid != stored_pid

            if differs or not new_pid:
                logger.debug(f"{pid_file} stale pid found attempted cleanup new {new_pid} vs old {stored_pid}")
                current = subprocess.run(
                    ["ps", "-o", "lstart=", "-p", str(stored_pid)],
                    capture_output=True,
                    text=True,
                ).stdout.strip()

                if current:
                    if current == stored_start:

                        # process_kill(stored_pid, platform, pid_file=pid_file) # psutil
                        res = drop_pid(stored_pid, pid_file=pid_file)
                        # if not res:
                        #   kill by pattern
                        #   fk_success = _fk_process(r'inotifywait.*-e create -e moved_to -e moved_from --format %e|%c|%w%f%0')
                        if not res:
                            return False  # In the rare case it wasnt previously shutdown prevented having two before starting this inotify process
                        # else:
                        # alternative
                        # try:
                        #     os.killpg(int(stored_pid), signal.SIGTERM)
                        # except OSError:
                        #     print(f"failed to close old pid {stored_pid} {stored_start}")
                        #     return False
                    else:
                        logger.debug(f"{pid_file} pid {stored_pid} reused by a different process, removing stale pidfile")
                else:
                    logger.debug("couldnt get process time from psutil oldpid skipping check")
        else:
            logger.error(f"incorrect format in {pid_file} couldnt parse in oldpid")

        os.remove(pid_file)  # normal clear the old pid file

    return res


def strup(script_dir, home_dir, inotify_creation_file, inotify_pid_file, inotify_debug_file, cdir, datadict, lockfile, log_file, _time, min_span, CACHE_F, CSZE, moduleNAME, supbrwLIST, algo, logger):

    script_path = os.path.join(script_dir, 'start_inotify')
    cmd = [
        script_path,
        str(inotify_creation_file),
        moduleNAME,
        str(CACHE_F),
        str(inotify_pid_file),
        str(inotify_debug_file),
        str(cdir),
        str(datadict),
        str(home_dir),
        str(lockfile),
        str(CSZE),
        str(algo),
        str(_time),
        str(min_span),
        *supbrwLIST
    ]
    try:
        script_dir = os.path.dirname(script_path)

        subprocess.run(cmd, cwd=script_dir, capture_output=True, text=True, check=True)

        logger.debug("strup completed successfully")

    except subprocess.CalledProcessError as e:
        print("xRC unable to start inotify logged to", log_file)
        logger.error(f"error in strup: {e} {type(e).__name__}", exc_info=True)
        combined = "\n".join(filter(None, [e.stdout, e.stderr]))
        if combined:
            logger.error("[OUTPUT]\n" + combined)
    except Exception as e:
        print("xRC exception in strup logged to", log_file)
        logger.error(f"strup General exception unable to start inotify wait: {e} {type(e).__name__}", exc_info=True)


def to_float_or_not(value, field, line, logger):
    """ for entropy value can be None so not unusual just return None. anything else log as DEBUG """
    if value in ("", "None", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as e:
        logger.debug(
            "parselog not a float %s: %r line: %s err: %s",
            field, value, line, e
        )
        return None


def to_int_or_not(value, field, line, logger):
    """ anything else None is not usual for value log it as ERROR if it fails """
    try:
        return int(value)
    except (TypeError, ValueError) as e:
        logger.error(
            "parselog invalid integer %s: %r line: %s err: %s",
            field, value, line, e
        )
        return None


def parse_line(line):
    quoted_match = QUOTED_RE.search(line)
    if not quoted_match:
        return None
    raw_filepath = quoted_match.group(1)

    filepath = raw_filepath  # escaped but decoded in parselog

    line_without_file = line.replace(quoted_match.group(0), '').strip()  # Remove quoted path
    other_fields = line_without_file.split()

    if len(other_fields) < 7:
        return None

    timestamp1_subfld1 = None if other_fields[0] in ("", "None") else other_fields[0]
    timestamp1_subfld2 = None if other_fields[1] in ("", "None") else other_fields[1]
    timestamp1 = None if not timestamp1_subfld1 or not timestamp1_subfld2 else f"{timestamp1_subfld1} {timestamp1_subfld2}"
    if timestamp1:
        timestamp1 = parse_datetime(timestamp1)
    if not timestamp1:
        return None

    timestamp2_subfld1 = None if other_fields[2] in ("", "None") else other_fields[2]
    timestamp2_subfld2 = None if other_fields[3] in ("", "None") else other_fields[3]
    timestamp2 = None if not timestamp2_subfld1 or not timestamp2_subfld2 else f"{timestamp2_subfld1} {timestamp2_subfld2}"

    inode = other_fields[4]

    timestamp3_subfld1 = None if other_fields[5] in ("", "None") else other_fields[5]
    timestamp3_subfld2 = None if other_fields[6] in ("", "None") else other_fields[6]
    timestamp3 = None if not timestamp3_subfld1 or not timestamp3_subfld2 else f"{timestamp3_subfld1} {timestamp3_subfld2}"

    rest = other_fields[7:]

    return [timestamp1, filepath, timestamp2, inode, timestamp3] + rest


def parselog(file, checksum, logger=logging):

    results = []

    for line in file:
        try:
            inputln = parse_line(line)
            if not inputln or not inputln[1].strip():
                logger.debug("parselog missing line or filename from input. skipping.. record: %s", line)
                continue

            n = len(inputln)

            if checksum:
                if n < 18:
                    print("parselog checksum, input out of boundaries skipping")
                    logger.debug("file: %s record length less than required 18. skipping.. record: %s", file, line)
                    continue
            else:
                if n < 10:
                    print("parselog no checksum, input out of boundaries skipping")
                    logger.debug("file %s record length less than required 10. skipping.. record: %s", file, line)
                    continue

            timestamp = inputln[0]

            filename = ap_decode(inputln[1])
            escf_path = escf_py(filename)

            changetime = inputln[2]
            ino = None if inputln[3] in ("", "None") else inputln[3]
            accesstime = inputln[4]
            checks = None if n > 5 and inputln[5] in ("", "None") else (inputln[5] if n > 5 else None)
            entropy = None if n > 6 and inputln[6] in ("", "None") else (inputln[6] if n > 6 else None)
            mime = None if n > 7 and inputln[7] in ("", "None") else (inputln[7] if n > 7 else None)
            sze = None if n > 8 and inputln[8] in ("", "None") else (inputln[8] if n > 8 else None)
            sym = None if n <= 9 or inputln[9] in ("", "None") else inputln[9]
            onr = None if n <= 10 or inputln[10] in ("", "None") else inputln[10]
            gpp = None if n <= 11 or inputln[11] in ("", "None") else inputln[11]
            pmr = None if n <= 12 or inputln[12] in ("", "None") else inputln[12]
            cam = None if n <= 13 or inputln[13] in ("", "None") else inputln[13]
            timestamp1 = None if n <= 14 or inputln[14] in ("", "None") else inputln[14]
            timestamp2 = None if n <= 15 or inputln[15] in ("", "None") else inputln[15]
            lastmodified = None if not timestamp1 or not timestamp2 else f"{timestamp1} {timestamp2}"
            hardlink = None if n <= 16 or inputln[16] in ("", "None") else inputln[16]
            us = None if n <= 17 or inputln[17] in ("", "None") else inputln[17]

            target = None
            if sym == 'y':
                try:
                    target = os.readlink(filename)
                except OSError:
                    logger.error("skipped error resolving symlink target, file: %s", filename)
                    continue

            inode = to_int_or_not(ino, "inode", line, logger)
            entropy = to_float_or_not(entropy, "entropy", line, logger) if checksum else entropy
            filesize = to_int_or_not(sze, "filesize", line, logger) if checksum else sze
            usec = to_int_or_not(us, "usec", line, logger) if checksum else us
            hardlink_count = to_int_or_not(hardlink, "hardlink_count", line, logger) if checksum else hardlink

            if not checksum:
                cam = checks
                timestamp1 = entropy
                timestamp2 = mime
                lastmodified = None if not timestamp1 or not timestamp2 else f"{timestamp1} {timestamp2}"
                usec = sze
                hardlink_count = sym
                checks = entropy = mime = filesize = sym = onr = gpp = None

            results.append((timestamp, filename, changetime, inode, accesstime, checks, entropy, mime, filesize, sym, onr, gpp, pmr, cam, target, lastmodified, hardlink_count, usec, escf_path))

        except Exception as e:
            print(f'Problem detected in parser parselog for line {line} err: {type(e).__name__}: {e} \n skipping..')
            logger.error("General error parselog , file %s  line: %s \n error: %s", file, line, type(e).__name__, exc_info=True)

    return results


def rotate_cache(cfr, cache_f, logger):
    created = {}
    if cache_f.is_file():
        rotated = cache_f.with_name(cache_f.name + ".old")
        if rotated.exists():
            logger.debug("old cachefile already existed %s", rotated)
            removefile(rotated)
        os.rename(cache_f, rotated)
        with rotated.open("r") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    logger.debug("Skipping possibly empty line from cache file: %s", line)
                    continue
                try:
                    metadata, checksum, entropy, mime, filepath = line.split("\t", maxsplit=4)
                    filepath = filepath.strip()
                    if not filepath:
                        logger.debug("Skipping malformed line in cache file with empty filepath: %s", line)
                        continue
                except ValueError:
                    print("Skipping malformed line in cache file")
                    logger.error("Failed to parse delimiter in cache file line: %s", line)
                    continue
                try:
                    _, size, mtime_epoch = metadata.split("|")  # inode not used
                    size = int(size)
                    mtime_epoch = int(mtime_epoch)
                except ValueError:
                    print(f"Skipping malformed metadata in cache file: {metadata}")
                    logger.error("Failed to parse metadata in cache file line: %s", line)
                    continue

                time_stamp_frm = epoch_to_date(mtime_epoch / 1_000_000)
                if time_stamp_frm:
                    time_stamp = time_stamp_frm.replace(microsecond=0)
                    logger.debug("Inserting %s %s %s %s %s %s %s", checksum, entropy, mime, size, time_stamp, mtime_epoch, filepath)
                    upt_cache(cfr, checksum, entropy, mime, size, time_stamp, mtime_epoch, filepath)

                    cache_data = {
                        'checksum': checksum,
                        'entropy': entropy,
                        'mime': mime
                    }

                    created[filepath] = cache_data
                else:
                    print("xRC invalid time_stamp or format detected in cache file.")
                    logger.debug("xRC Invalid timestamp in cache file line: %s", line)
        removefile(rotated)
    return created


# file_creation_log.txt
def parse_tout(log_file, checksum, logger):
    """ this is unused """
    tout_files = []
    all_files = []

    rotated = log_file.with_name(log_file.name + ".old")
    if os.path.exists(rotated):
        logger.debug("init_recentchanges old tout already existed %s", rotated)
        removefile(rotated)
    os.rename(log_file, rotated)

    with rotated.open('r') as f:
        tout_files = f.readlines()

    if tout_files:
        all_files = parselog(tout_files, checksum, logger)

    removefile(rotated)
    return all_files


def time_extract(line, tout_file, logger):
    parts = line.split(maxsplit=2)
    if len(parts) < 2:
        logger.error("trim_tout time_extract while parsing log impartial line couldnt get mtime. skipping.. record: %s file: %s", line, tout_file)
        return 0
    if parts[0] == "None" or parts[1] == "None":
        logger.error("trim_tout time_extract while parsing log impartial line couldnt get mtime. skipping.. record: %s file: %s", line, tout_file)
        return 0
    dt = parse_datetime(f"{parts[0]} {parts[1]}")
    return dt.timestamp() if dt else 0


def time_extract_str(line, tout_file, logger):
    parts = line.split(maxsplit=2)
    if len(parts) < 2:
        logger.error("trim_tout time_extract while parsing log impartial line couldnt get mtime. skipping.. record: %s file: %s", line, tout_file)
        return ""
    if parts[0] == "None" or parts[1] == "None":
        logger.error("trim_tout time_extract while parsing log impartial line couldnt get mtime. skipping.. record: %s file: %s", line, tout_file)
        return ""
    return f"{parts[0]} {parts[1]}"


def trim_tout(log_file, time_back=6, trim_to=9, min_span_hours=0, logger=logging):
    """ trim created log file.
        by span trim the borderline. if exceeded clear file_creation_log.txt
        or by rolling waterline """

    cutoff_time = time.time()

    if os.path.isfile(log_file):

        try:

            with log_file.open('r') as f:
                tout_files = f.readlines()

            if tout_files:

                first_ts = time_extract(tout_files[0], log_file, logger)

                # by span
                if min_span_hours:
                    # get the last file and get the span
                    last_ts = time_extract(tout_files[-1], log_file, logger)
                    span = (last_ts - first_ts) / 3600  # hours

                    if span > min_span_hours:
                        removefile(log_file)
                        return True

                # by rolling. trim to low water
                elif trim_to:
                    # is it at high water
                    trim = (cutoff_time - first_ts) > (trim_to * 3600)

                    if trim:
                        if trim_to < time_back:
                            print("trim_tout low water was higher than high water defaulting to high water", trim_to)
                            time_back = trim_to
                        cutoff_time = cutoff_time - (time_back * 3600)
                        fmt = "%Y-%m-%d %H:%M:%S"
                        cutoff_str = datetime.fromtimestamp(cutoff_time).strftime(fmt)
                        kept = [line for line in tout_files if time_extract_str(line, log_file, logger) >= cutoff_str]
                        if kept:
                            with open(log_file, 'w') as f:
                                f.writelines(kept)
                        else:
                            removefile(log_file)
                        return True

        except Exception as e:
            print(f'trim_tout problem detected in parser parselog err: {type(e).__name__}: {e} \n skipping..')
            logger.error("trim_tout General error parselog , file %s \n error: %s", log_file, type(e).__name__, exc_info=True)
            return None

    return False


def init_recentchanges(script_dir, home_dir, cfr, xRC, _time, min_span, checksum, moduleNAME, log_path, supbrwLIST, algo='md5'):

    # to kill inotifywait script
    # sudo pkill -f 'inotifywait.*-e create -e moved_to -e moved_from --format %e|%c|%w%f%0'
    # or
    # kill -SIGTERM -<pid>

    inotify_log_file = "file_creation_log.txt"
    inotify_debug_file = "inotify.log"

    CSZE = 1024 * 1024  # 1MB save to cache created files
    logger = logging.getLogger("INITRECENTCHANGES")

    created = {}

    try:
        temp_base = Path("/tmp")

        # inotify_creation_file main output  /tmp/file_creation_log.txt
        # CACHE_F cache output                   /tmp/dbctimecache/ctimecache
        # datadict dir for caching system     /tmp/dbctimecache/datadict/
        # inotify_pid_file                                  /tmp/inotify_watcher.pid
        # lockfile                                              /tmp/pblk.lock

        search_pattern = os.path.join(script_dir.name, "inotify")
        cdir = temp_base / "dbctimecache"
        inotify_creation_file = temp_base / inotify_log_file
        inotify_debug_file = temp_base / inotify_debug_file
        CACHE_F = cdir / "ctimecache"
        datadict = cdir / "datadict"

        inotify_pid_file = os.path.join(temp_base, 'inotify_watcher.pid')
        lockfile = "/tmp/pblk.lock"

        fk_success = True

        # pid = process_by_target(search_pattern)
        # if pid:
        if process_status(search_pattern):

            # if multiple processes
            # inotify wait is running wait until it is finished if it is in the middle of a write

            # fd = os.open(lockfile, os.O_WRONLY | os.O_CREAT, 0o644)
            # os.dup2(fd, 200)
            # os.close(fd)

            # lock_fd = 200
            # try:
            # fcntl.flock(lock_fd, fcntl.LOCK_EX)
            # lock_ = True

            # kill inotify wait process results and restart the timer
            if checksum and xRC:

                os.makedirs(cdir, mode=0o700, exist_ok=True)

                # killed = drop_pid(pid)
                fk_success = _fk_process(r'inotifywait.*-e create -e moved_to -e moved_from --format %e|%c|%w%f%0')

                # a partial write could occur but would get parsed out and is insignificant this avoids the use of locks currently

                created = rotate_cache(cfr, CACHE_F, logger)

                # if os.path.isfile(inotify_creation_file):
                #    all_files = parse_tout(inotify_creation_file, checksum, logger)
                # open(inotify_creation_file, 'w').close()

                if fk_success or not process_status(search_pattern):
                    strup(
                        script_dir, home_dir, inotify_creation_file, inotify_pid_file, inotify_debug_file, cdir, datadict, lockfile,
                        log_path, _time, min_span, CACHE_F, CSZE, moduleNAME, supbrwLIST, algo, logger
                    )
                elif fk_success:
                    logger.error("inotifywait was already running continuing")  # log unusual event

                # else:
                #     logging.debug("couldnt close inotify script checking for pid file")
                #     new_pid = None
                #     if not old_pid_check(inotify_pid_file, new_pid, logging):
                #         with inotify_debug_file.open("a") as f:
                #             f.write("failed to close a previously running process\n")
                #     else:
                #         if not process_status(search_pattern):
                #             strup(
                #                 script_dir, home_dir, inotify_creation_file, inotify_pid_file, inotify_debug_file, cdir, datadict, lockfile,
                #                 log_path, _time, min_span, CACHE_F, CSZE, moduleNAME, supbrwLIST, algo, logger
                #             )
                #         else:
                #             with inotify_debug_file.open("a") as f:
                #                 f.write("failed to start xRC cannot start with a previous running process\n")

            # the setting was turned off kill inotify wait
            else:

                fk_success = _fk_process(r'inotifywait.*-e create -e moved_to -e moved_from --format %e|%c|%w%f%0')

            if not fk_success:
                logging.debug("_fk_process did not report success for inotifywait termination")  # log second unusual event
            # except OSError as e:
            #     logger.error(f"Failed to acquire lock: {e}")
            # finally:
            #     if lock_:
            #         fcntl.flock(lock_fd, fcntl.LOCK_UN)
            #     os.close(lock_fd)

        # first start
        elif checksum and xRC:
            os.makedirs(cdir, mode=0o700, exist_ok=True)
            strup(
                script_dir, home_dir, inotify_creation_file, inotify_pid_file, inotify_debug_file, cdir, datadict, lockfile,
                log_path, _time, min_span, CACHE_F, CSZE, moduleNAME, supbrwLIST, algo, logger
            )

    except Exception as e:
        logging.error(f"Error in xRC error: {e} {type(e).__name__}", exc_info=True)

    return created
# end xRC functions
