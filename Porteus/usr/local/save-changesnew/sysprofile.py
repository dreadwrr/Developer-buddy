import logging
import subprocess
import os
import pathlib
import sys
import traceback
from pathlib import Path
from fsearch import process_lines
from pyfunctions import cprint
# 01/03/2026 proteus shield sys profile


def collect_layer_files(layer, subdirs, log_path, logger, match_args=None):

    all_file_entries = []
    file_entries = []

    try:
        for subdir in subdirs:
            dir_path = os.path.join(layer, subdir)
            if not os.path.isdir(dir_path):
                continue

            cmd = ["sudo", "find", layer, "-path", f"{dir_path}/*", "-type", "f"]
            if match_args:
                cmd += match_args
            cmd += ["-printf", "%T@ %A@ %C@ %i %M %s %u %g %m /%P\\0"]

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, err = proc.communicate()

            if proc.returncode != 0:
                logger.error("Find command error: %s\n", err.decode('utf-8', errors='replace'))
                raise subprocess.CalledProcessError(proc.returncode, cmd)

            if output:
                file_entries = [entry.decode('utf-8', errors='replace') for entry in output.split(b'\0') if entry]
                all_file_entries.extend(file_entries)

    except Exception as e:
        print("General error in collect_layer_files. Log file:", log_path)
        logger.error(f"There was an error in collect_layer_files err: {e} {type(e).__name__}", exc_info=True)
    return all_file_entries


def process_category(xdata, layers, category, subdirs, log_path, logger):
    all_entries = []

    for layer in layers:
        dirname = os.path.basename(str(layer))
        if dirname.startswith("000"):
            continue  # skip kernel/firmware

        match_args = []
        if category == "binary":
            match_args = ["-executable"]
        elif category == "library":
            match_args = ["-name", "*.so*"]

        entries = collect_layer_files(str(layer), subdirs, log_path, logger, match_args)
        all_entries.extend(entries)

    if all_entries:
        xdata.extend(all_entries)


def collect_all_files_to_array(ch_base, systemf, log_path, logger):

    try:
        layers = [f"{ch_base}{str(i).zfill(3)}" for i in range(4)]
        layers += list(pathlib.Path(ch_base).glob("00[0-3]-*"))

        for folder in layers:
            folder = str(folder)
            if not os.path.isdir(folder):
                continue

            cmd = ["sudo", "find", folder, "-type", "f", "-printf", "%T@ %A@ %C@ %i %M %s %u %g %m /%P\\0"]  # # %y shows f for file , l for sym
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)

            if proc.stdout is None:
                logger.debug(f"sysprofile Failed to capture stdout for {folder}")
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
                        systemf.append(part.decode("utf-8", errors="replace"))

            if buffer.strip():
                try:
                    systemf.append(buffer.decode("utf-8", errors="replace"))
                except Exception:
                    pass

            proc.stdout.close()
            proc.wait()
            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, cmd)
    except Exception as e:
        print("General error in collect_all_files_to_array. Log file:", log_path)
        logger.error(f"There was an error in collect_all_files_to_array err: {e} {type(e).__name__}", exc_info=True)


def main(turbo, logging_values):

    systemf = []  # all files
    xdata = []   # files to hash
    COMPLETE = []  # nsf
    SORTCOMPLETE = []

    COMPLETE_1 = []  # nsf perms?
    COMPLETE_2 = []
    xdata_raw = []
    diff = []

    ch = "/mnt/live/memory/images"
    CACHE_F = "/dev/null"

    logger = logging.getLogger("SYSPROFILE")

    log_path = None
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.FileHandler):
            log_path = Path(handler.baseFilename)
            break
    # root = logging.getLogger()
    # for h in root.handlers:
    #     if isinstance(h, logging.FileHandler):
    #         log_path = Path(h.baseFilename)
    #         break

    cprint.cyan('Generating system profile from base .xzms.')
    print("Turbo is:", turbo)

    collect_all_files_to_array(ch, systemf, log_path, logger)

    layers = list(Path(ch).glob("00[1-3]-*"))

    categories = {
        "binary": ["bin", "etc", "sbin", "usr", "opt/porteus-scripts"],
        "sects": ["etc", "home", "root"],
        "library": ["lib", "lib64", "usr/lib", "usr/lib64", "var/lib"]
    }

    for category, subdirs in categories.items():
        process_category(xdata_raw, layers, category, subdirs, log_path, logger)

    systemf_set = set(systemf)
    xdata_set = set(xdata_raw)

    diff = systemf_set - xdata_set

    search_start_dt = None
    xdata, COMPLETE_2 = process_lines(xdata_raw, turbo, True, False, "main", "sys", search_start_dt, "PROCESS_SYS", logging_values, CACHE_F)
    systemf, COMPLETE_1 = process_lines(list(diff), turbo, False, False, "main", "sys", search_start_dt, "PROCESS_SYS", logging_values, CACHE_F)

    SORTCOMPLETE = xdata + systemf

    if SORTCOMPLETE:
        return SORTCOMPLETE
    else:
        logger.debug("SORTCOMPLETE was empty.")
        return None


if __name__ == "__main__":
    try:
        main(*sys.argv[1:])
    except Exception as e:
        print(f'Error: {e} {type(e).__name__} \n {traceback.format_exc()}', file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
