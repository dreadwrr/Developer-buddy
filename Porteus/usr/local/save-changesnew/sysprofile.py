import logging
import subprocess
import os
import sys
import traceback
from pathlib import Path
from fsearch import process_lines
from pyfunctions import cprint


# 02/26/2026 proteus shield sys profile


def collect_layer_files(layer, subdirs, is_sym, match_args=None):

    all_file_entries = []
    file_entries = []
    cc1 = ["-type", "f"]
    cc2 = ["-not", "-type", "d"]

    adtcmd = cc1 if not is_sym else cc2

    TAIL = ["-printf", "%T@ %A@ %C@ %i %M %n %s %u %g %m /%P\\0"]
    for subdir in subdirs:
        dir_path = os.path.join(layer, subdir)
        if not os.path.isdir(dir_path):
            continue

        cmd = ["find", layer, "-path", f"{dir_path}/*"] + adtcmd

        if match_args:
            cmd += match_args
        cmd += TAIL

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, err = proc.communicate()

        if proc.returncode != 0:
            print(f"collect_layer_files Find command return_code: {proc.returncode} \n error: {err.decode('utf-8', errors='replace')}")
            raise subprocess.CalledProcessError(proc.returncode, cmd)

        if output:
            file_entries = [entry.decode('utf-8', errors='replace') for entry in output.split(b'\0') if entry]
            all_file_entries.extend(file_entries)

    return all_file_entries


def process_category(layers, category, subdirs, is_sym, logger):

    all_entries = {}

    for layer in layers:
        dirname = os.path.basename(str(layer))
        if dirname.startswith("000"):
            continue  # skip kernel/firmware

        match_args = []
        if category == "binary":
            match_args = ["-executable"]
        if category == "library":
            match_args = ["-name", "*.so*"]

        entries = collect_layer_files(str(layer), subdirs, is_sym, match_args)
        if entries:
            for entry in entries:
                fields = entry.split(maxsplit=10)
                if len(fields) < 11:
                    logger.debug("process_category record length < 11. skipping: %s", entry)
                    continue
                filename = fields[10]
                if filename in all_entries:
                    continue
                all_entries[filename] = tuple(fields)

    return all_entries


def collect_all_files_to_array(all_layers, is_sym, logger):

    set_seen = set()
    all_files = []

    cc1 = ["-type", "f"]
    cc2 = ["-not", "-type", "d"]
    TAIL = ["-printf", "%T@ %A@ %C@ %i %M %n %s %u %g %m /%P\\0"]
    if not is_sym:
        TAIL = cc1 + TAIL
    else:
        TAIL = cc2 + TAIL

    for folder in all_layers:
        records = []
        folder = str(folder)
        if not os.path.isdir(folder):
            continue

        cmd = ["find", folder] + TAIL  # # Using %M  instead of %y shows f for file , l for sym
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if proc.stdout is None:
            logger.debug("Failed to capture stdout for %s", folder)
            continue

        buffer = b""
        while True:
            chunk = proc.stdout.read(8192)
            if not chunk:
                break
            buffer += chunk
            while b'\0' in buffer:
                part, buffer = buffer.split(b'\0', 1)
                if part.strip():
                    records.append(part.decode("utf-8", errors="replace"))

        if buffer.strip():
            try:
                records.append(buffer.decode("utf-8", errors="replace"))
            except Exception:
                pass

        proc.stdout.close()
        proc.wait()

        if proc.returncode != 0:
            err = proc.stderr.read()
            proc.stderr.close()
            print(f"collect_all_files_to_array Find command return_code: {proc.returncode} \n error: {err.decode('utf-8', errors='replace')}")
            raise subprocess.CalledProcessError(proc.returncode, cmd)

        if records:
            for record in records:
                fields = record.split(maxsplit=10)
                if len(fields) < 11:
                    logger.debug("record length < 11. skipping: %s", record)
                    continue
                filename = fields[10]
                if filename in set_seen:
                    continue
                all_files.append(tuple(fields))
                set_seen.add(filename)

    return all_files


def main(turbo, logging_values):

    systemf = []  # all files
    xdata = []   # files to hash
    # COMPLETE = []  # nsf
    SORTCOMPLETE = []

    COMPLETE_1, COMPLETE_2 = [], []  # nsf perms?

    xdata_raw = []
    diff = []

    all_layers = []
    ch = "/mnt/live/memory/images"
    CACHE_F = "/dev/null"

    is_sym = True  # include symlinks

    logger = logging.getLogger("SYSPROFILE")
    log_path = logging_values[0]
    cprint.cyan('Generating system profile from base .xzms.')
    print("Turbo is:", turbo)

    all_layers += list(Path(ch).glob("000-*"))  # kernel # layers = [f"{ch_base}{str(i).zfill(3)}" for i in range(4)]  # /mnt/live/memory/images000 , images001 ect test

    xzms = ['003', '002', '001']
    layers = []
    for layer in xzms:
        p = f"{layer}-*"
        files = list(Path(ch).glob(p))
        layers.extend(files)

    all_layers += layers

    try:
        systemf = collect_all_files_to_array(all_layers, is_sym, logger)
    except Exception as e:
        emsg = f"Exception {e} {type(e).__name__} Log file: {log_path}"
        print(emsg)
        logger.error(emsg, exc_info=True)
        return None

    categories = {
        "binary": ["bin", "etc", "sbin", "usr", "opt/porteus-scripts"],
        "sects": ["etc", "home", "root"],
        "library": ["lib", "lib64", "usr/lib", "usr/lib64", "var/lib"]
    }

    if systemf:
        logger = logging.getLogger("process_category")
        matches = {}
        try:
            for category, subdirs in categories.items():
                found_files = process_category(layers, category, subdirs, is_sym, logger)
                if found_files:
                    for key, value in found_files.items():
                        if key not in matches:
                            matches[key] = value
            if not matches:
                print("no matches from sys profile")
                return []
        except Exception as e:
            emsg = f"Exception {e} {type(e).__name__}. Log file: {log_path}"
            print(emsg)
            logger.error(emsg, exc_info=True)
            return None

        xdata_raw = list(matches.values())

        xdata_set = set(xdata_raw)
        systemf_set = set(systemf)

        diff = list(systemf_set - xdata_set)

        user_setting = {
            'mMODE': turbo,
            'checksum': True
        }
        search_start_dt = None

        xdata, COMPLETE_2 = process_lines(xdata_raw, "main", "sys", search_start_dt, "PROCESS_SYS", user_setting, logging_values, CACHE_F)

        user_setting['checksum'] = False
        systemf, COMPLETE_1 = process_lines(list(diff), "main", "sys", search_start_dt, "PROCESS_SYS", user_setting, logging_values, CACHE_F)

        SORTCOMPLETE = xdata + systemf

        if SORTCOMPLETE:
            return SORTCOMPLETE
        else:
            logger.debug("SORTCOMPLETE was empty.")
            return []
    return []


if __name__ == "__main__":
    try:
        main(*sys.argv[1:])
    except Exception as e:
        print(f'Error: {e} {type(e).__name__} \n {traceback.format_exc()}', file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
