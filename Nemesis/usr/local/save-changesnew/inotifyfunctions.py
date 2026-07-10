import logging
import os
import re
import signal
import subprocess
import time
from pathlib import Path
from fsearchfunctions import upt_cache
from pyfunctions import ap_decode
from pyfunctions import epoch_to_date
from pyfunctions import escf_py
from pyfunctions import parse_datetime
from rntchangesfunctions import removefile
# 07/10/2026


# Globals
QUOTED_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')

# xRC functions


def process_status(pattern):
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


def _fk_process(pattern):
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


# formerly named shutdown
def drop_pid(pid, pid_file):
    try:
        os.kill(-pid, signal.SIGTERM)
        removefile(pid_file)
        return True
    except ProcessLookupError:
        pass  # already gone
    except PermissionError:
        print("shutdown func inotifywait permission error")
    return False


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


def oldpid(pidfile):
    """ read from the stored format the pid file that start inotifywait made """
    res = False

    if os.path.isfile(pidfile):
        with open(pidfile) as f:
            stored_pid, stored_start = f.read().rstrip("\n").split("|", 1)

        current = subprocess.run(
            ["ps", "-o", "lstart=", "-p", stored_pid],
            capture_output=True,
            text=True,
        ).stdout.strip()

        if current:
            if current == stored_start:
                try:
                    os.killpg(int(stored_pid), signal.SIGTERM)
                except OSError:
                    print(f"failed to close old pid {stored_pid} {stored_start}")
                    res = True

        os.remove(pidfile)

    return res


def old_pid_check(watchdog_pid_file, new_pid, platform, logger=logging):
    """ This is from qt version. instead implemented above in a different format.
        if there is an old pid file try to kill. """

    pid = get_pid(watchdog_pid_file)
    if pid:
        differs = new_pid and new_pid != pid
        if differs or not new_pid:
            logger.debug(f"{watchdog_pid_file} stale pid found attempted cleanup new {new_pid} vs old {pid}")
            if platform == "linux":
                # process_kill(pid)
                drop_pid(pid, platform, watchdog_pid_file)
                # if not res:
                #   kill by pattern
                #   fk_success = _fk_process(r'inotifywait.*-e create -e moved_to --format %e\|%w%f%0')  # fk_success = _fk_process('inotifywait -m -r -e create -e moved_to --format %e|%w%f%0')  # original
            else:
                drop_pid(pid, watchdog_pid_file)


def strup(script_dir, home_dir, inotify_creation_file, cdir, lockfile, log_file, _time, min_span, CACHE_F, CSZE, checksum, moduleNAME, logger, supbrwLIST):

    script_path = os.path.join(script_dir, 'start_inotify')
    cmd = [
        script_path,
        str(inotify_creation_file),
        moduleNAME,
        str(CACHE_F),
        str(CSZE),
        str(cdir),
        str(home_dir),
        str(lockfile),
        str(checksum).lower(),
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
        print("xRC logged an exception to", log_file)
        logger.error(f"strup General exception unable to start inotify wait: {e} {type(e).__name__}", exc_info=True)


def _to_int_or_none(value, field, line):
    if value in ("", "None", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        logging.debug(
            "parselog invalid integer %s: %r line: %s",
            field, value, line
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


def parselog(file, checksum):

    results = []

    for line in file:
        try:
            inputln = parse_line(line)
            if not inputln or not inputln[1].strip():
                logging.debug("parselog missing line or filename from input. skipping.. record: %s", line)
                continue

            n = len(inputln)

            if checksum:
                if n < 15:
                    print("parselog checksum, input out of boundaries skipping")
                    logging.debug("table: %s record length less than required 15. skipping.. record: %s", line)
                    continue
            else:
                if n < 10:
                    print("parselog no checksum, input out of boundaries skipping")
                    logging.debug("table %s record length less than required 10. skipping.. record: %s", line)
                    continue

            timestamp = inputln[0]

            filename = ap_decode(inputln[1])
            escf_path = escf_py(filename)

            changetime = inputln[2]
            ino = None if inputln[3] in ("", "None") else inputln[3]
            accesstime = inputln[4]
            checks = None if n > 5 and inputln[5] in ("", "None") else (inputln[5] if n > 5 else None)
            sze = None if n > 6 and inputln[6] in ("", "None") else (inputln[6] if n > 6 else None)
            sym = None if n <= 7 or inputln[7] in ("", "None") else inputln[7]
            onr = None if n <= 8 or inputln[8] in ("", "None") else inputln[8]
            gpp = None if n <= 9 or inputln[9] in ("", "None") else inputln[9]
            pmr = None if n <= 10 or inputln[10] in ("", "None") else inputln[10]
            cam = None if n <= 11 or inputln[11] in ("", "None") else inputln[11]
            timestamp1 = None if n <= 12 or inputln[12] in ("", "None") else inputln[12]
            timestamp2 = None if n <= 13 or inputln[13] in ("", "None") else inputln[13]
            lastmodified = None if not timestamp1 or not timestamp2 else f"{timestamp1} {timestamp2}"
            hardlink = None if n <= 14 or inputln[14] in ("", "None") else inputln[14]
            us = None if n <= 15 or inputln[15] in ("", "None") else inputln[15]

            target = None
            if sym == 'y':
                try:
                    target = os.readlink(filename)
                except OSError:
                    logging.error("skipped error resolving symlink target, file: %s", filename)
                    continue

            inode = _to_int_or_none(ino, "inode", line)
            filesize = _to_int_or_none(sze, "filesize", line) if checksum else sze
            usec = _to_int_or_none(us, "usec", line) if checksum else us
            hardlink_count = _to_int_or_none(hardlink, "hardlink_count", line) if checksum else hardlink

            if not checksum:
                cam = checks
                timestamp1 = filesize
                timestamp2 = sym
                lastmodified = None if not timestamp1 or not timestamp2 else f"{timestamp1} {timestamp2}"
                usec = onr
                hardlink_count = gpp
                checks = filesize = sym = onr = gpp = None

            results.append((timestamp, filename, changetime, inode, accesstime, checks, filesize, sym, onr, gpp, pmr, cam, target, lastmodified, hardlink_count, usec, escf_path))

        except Exception as e:
            print(f'Problem detected in parser parselog for line {line} err: {type(e).__name__}: {e} \n skipping..')
            logging.error("General error parselog , file %s  line: %s \n error: %s", file, line, type(e).__name__, exc_info=True)

    return results


def rotate_cache(cfr, cache_f, logger):
    if cache_f.is_file():
        rotated = cache_f.with_name(cache_f.name + ".old")
        if rotated.exists():
            logger.debug("init_recentchanges old cachefile already existed %s", rotated)
            removefile(rotated)
        os.rename(cache_f, rotated)
        with rotated.open("r") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    logger.debug("Skipping possibly empty line from cache file: %s", line)
                    continue
                try:
                    metadata, checksum, filepath = line.split("\t", maxsplit=2)
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
                    logger.debug("Inserting %s %s %s %s %s", checksum, size, time_stamp, mtime_epoch, filepath)
                    upt_cache(cfr, checksum, size, time_stamp, mtime_epoch, filepath)
                else:
                    print("xRC invalid time_stamp or format detected in cache file.")
                    logger.debug("xRC Invalid timestamp in cache file line: %s", line)
        removefile(rotated)


def parse_tout(log_file, checksum, logger):
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


def trim_tout(log_file, time_back=6, trim_to=9, min_span_hours=0, logger=logging):
    """ trim created log file.
        by span trim the borderline.
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
                        kept = [line for line in tout_files if time_extract(line, log_file, logger) >= cutoff_time]
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


def init_recentchanges(script_dir, home_dir, cfr, xRC, _time, min_span, checksum, moduleNAME, log_path, supbrwLIST):

    inotify_log_file = "file_creation_log.txt"
    CSZE = 1024 * 1024  # 1MB save to cache created files
    logger = logging.getLogger("INITRECENTCHANGES")

    try:
        temp_base = Path("/tmp")

        search_pattern = os.path.join(script_dir.name, "inotify")
        cdir = temp_base / "dbctimecache"
        inotify_creation_file = temp_base / inotify_log_file
        CACHE_F = cdir / "ctimecache"

        inotify_pid = os.path.join(temp_base, 'inotify_watcher.pid')
        lockfile = "/tmp/pblk.lock"

        fk_success = True

        if process_status(search_pattern):

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

                # if the pid file is written see if it can be closed
                if not oldpid(inotify_pid):
                    # if couldnt not try by pattern
                    fk_success = _fk_process(r'inotifywait.*-e create -e moved_to -e moved_from --format %e|%c|%w%f%0')  # fk_success = _fk_process('inotifywait -m -r -e create -e moved_to --format %e|%w%f%0')  # original

                rotate_cache(cfr, CACHE_F, logger)

                # if os.path.isfile(inotify_creation_file):
                #    all_files = parse_tout(inotify_creation_file, checksum, logger)
                # open(inotify_creation_file, 'w').close()

                if fk_success or not process_status(search_pattern):
                    strup(script_dir, home_dir, inotify_creation_file, cdir, lockfile, log_path, _time, min_span, CACHE_F, CSZE, checksum, moduleNAME, logger, supbrwLIST)
                else:
                    if fk_success:
                        logging.debug("init_recentchanges inotifywait was already running continuing")  # log unusual event

            # the setting was turned off kill inotify wait
            else:

                if not oldpid(inotify_pid):
                    fk_success = _fk_process(r'inotifywait.*-e create -e moved_to -e moved_from --format %e|%c|%w%f%0')  # fk_success = _fk_process('inotifywait -m -r -e create -e moved_to --format %e|%w%f%0')  # original

            if not fk_success:
                logging.debug("init_recentchanges _fk_process did not report success for inotifywait termination")  # log second unusual event
            # except OSError as e:
            #     logger.error(f"Failed to acquire lock: {e}")
            # finally:
            #     if lock_:
            #         fcntl.flock(lock_fd, fcntl.LOCK_UN)
            #     os.close(lock_fd)

        # first start
        elif checksum and xRC:
            os.makedirs(cdir, mode=0o700, exist_ok=True)

            strup(script_dir, home_dir, inotify_creation_file, cdir, lockfile, log_path, _time, min_span, CACHE_F, CSZE, checksum, moduleNAME, logger, supbrwLIST)

    except Exception as e:
        logging.error(f"Error in xRC error: {e} {type(e).__name__}", exc_info=True)

# end xRC functions
