import logging
import os
import re
import subprocess
from pathlib import Path
from fsearchfunctions import upt_cache
from pyfunctions import ap_decode
from pyfunctions import epoch_to_date
from pyfunctions import escf_py
from pyfunctions import parse_datetime
from rntchangesfunctions import removefile

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


def strup(script_dir, home_dir, inotify_creation_file, CACHE_F, checksum, MODULENAME, log_file):

    script_path = os.path.join(script_dir, 'start_inotify')
    cmd = [
        script_path,
        str(inotify_creation_file),
        MODULENAME,
        str(CACHE_F),
        str(checksum).lower(),
        str(home_dir),
        "ctime",
        "3600"
    ]
    try:
        script_dir = os.path.dirname(script_path)
        subprocess.run(cmd, cwd=script_dir, capture_output=True, text=True, check=True)
        logging.debug("strup completed successfully")
    except subprocess.CalledProcessError as e:
        print("xRC unable to start inotify logged to", log_file)
        logging.error(f"error in strup: {e} {type(e).__name__}", exc_info=True)
        combined = "\n".join(filter(None, [e.stdout, e.stderr]))
        if combined:
            logging.error("[OUTPUT]\n" + combined)
    except Exception as e:
        print("xRC logged an exception to", log_file)
        logging.error(f"strup General exception unable to start inotify wait: {e} {type(e).__name__}", exc_info=True)


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
                logging.debug("parselog missing line or filename from input , table: %s. skipping.. record: %s", line)
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
            logging.error("General error parselog , table %s  line: %s \n error: %s", line, type(e).__name__, exc_info=True)

    return results


def rotate_cache(cfr, CACHE_F):
    if CACHE_F.is_file():
        rotated = CACHE_F.with_name(CACHE_F.name + ".old")
        if rotated.exists():
            logging.debug("init_recentchanges old cachefile already existed %s", rotated)
            removefile(rotated)
        os.rename(CACHE_F, rotated)
        with rotated.open("r") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    logging.debug("Skipping possibly empty line from cache file: %s", line)
                    continue
                try:
                    metadata, checksum, filepath = line.split("\t", maxsplit=2)
                    filepath = filepath.strip()
                    if not filepath:
                        logging.debug("Skipping malformed line in cache file with empty filepath: %s", line)
                        continue
                except ValueError:
                    print("Skipping malformed line in cache file")
                    logging.error("Failed to parse delimiter in cache file line: %s", line)
                    continue
                try:
                    _, size, mtime_epoch = metadata.split("|")  # inode not used
                    size = int(size)
                    mtime_epoch = int(mtime_epoch)
                except ValueError:
                    print(f"Skipping malformed metadata in cache file: {metadata}")
                    logging.error("Failed to parse metadata in cache file line: %s", line)
                    continue

                time_stamp_frm = epoch_to_date(mtime_epoch / 1_000_000)
                if time_stamp_frm:
                    time_stamp = time_stamp_frm.replace(microsecond=0)
                    logging.debug("Inserting %s %s %s %s %s", checksum, size, time_stamp, mtime_epoch, filepath)
                    upt_cache(cfr, checksum, size, time_stamp, mtime_epoch, filepath)
                else:
                    print("xRC invalid time_stamp or format detected in cache file.")
                    logging.debug("xRC Invalid timestamp in cache file line: %s", line)
        removefile(rotated)


def parse_tout(log_file, checksum):
    tout_files = []
    all_files = []

    rotated = log_file.with_name(log_file.name + ".old")
    if os.path.exists(rotated):
        logging.debug("init_recentchanges old tout already existed %s", rotated)
        removefile(rotated)
    os.rename(log_file, rotated)

    with rotated.open('r') as f:
        tout_files = f.readlines()

    if tout_files:
        all_files = parselog(tout_files, checksum)

    removefile(rotated)
    return all_files


def init_recentchanges(script_dir, home_dir, inotify_creation_file, cfr, xRC, checksum, MODULENAME, log_path):
    try:
        all_files = []
        search_pattern = os.path.join(script_dir.name, "inotify")

        if checksum and xRC:

            cached = Path("/tmp/dbctimecache/")

            CACHE_F = cached / "ctimecache"

            os.makedirs(cached, mode=0o700, exist_ok=True)

            if process_status(search_pattern):
                fk_success = _fk_process('inotifywait -m -r -e create -e moved_to --format %e|%w%f%0')
                rotate_cache(cfr, CACHE_F)

                if os.path.isfile(inotify_creation_file):

                    all_files = parse_tout(inotify_creation_file, checksum)

                open(inotify_creation_file, 'w').close()
                if fk_success or not process_status(search_pattern):
                    strup(script_dir, home_dir, inotify_creation_file, CACHE_F, checksum, MODULENAME, log_path)
                else:
                    removefile(inotify_creation_file)
            else:
                removefile(inotify_creation_file)
                strup(script_dir, home_dir, inotify_creation_file, CACHE_F, checksum, MODULENAME, log_path)
        else:
            if process_status(search_pattern):
                fk_success = _fk_process('inotifywait -m -r -e create -e moved_to --format %e|%w%f%0')
                if not fk_success:
                    logging.debug("init_recentchanges _fk_process did not report success for inotifywait termination")
                removefile(inotify_creation_file)
        return all_files
    except Exception as e:
        logging.error(f"Error in xRC error: {e} {type(e).__name__}", exc_info=True)
    return []

# end xRC functions
