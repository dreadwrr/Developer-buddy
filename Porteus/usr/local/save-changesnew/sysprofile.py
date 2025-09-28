# 09/26/2025 proteus shield sys profile
import subprocess
import os
import pathlib
import sys
from fsearch import process_find_lines


def collect_layer_files(layer, subdirs, match_args=None):
    all_file_entries = []

    for subdir in subdirs:
        dir_path = os.path.join(layer, subdir)
        if not os.path.isdir(dir_path):
            continue

        cmd = ["find", dir_path, "-type", "f"]
        if match_args:
            cmd += match_args
        cmd += ["-printf", "%T@ %A@ %C@ %i %s %u %g %m %p\\0"]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, err = proc.communicate()

        if proc.returncode != 0:
            print(f"Find command error:\n{err.decode('utf-8', errors='replace')}")
            raise subprocess.CalledProcessError(proc.returncode, cmd)

        if output:
            file_entries = [entry.decode('utf-8', errors='replace') for entry in output.split(b'\0') if entry]
            all_file_entries.extend(file_entries)

    return all_file_entries


def process_category(xdata, COMPLETE, layers, category, subdirs, CACHE_F, CSZE):
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

        entries = collect_layer_files(str(layer), subdirs, match_args)
        all_entries.extend(entries)

    if all_entries:
        xdata.extend(all_entries)


def collect_all_files_to_array(ch_base, systemf):
    layers = [f"{ch_base}{str(i).zfill(3)}" for i in range(4)]
    layers += list(pathlib.Path(ch_base).glob("00[0-3]-*"))

    for folder in layers:
        folder = str(folder)
        if not os.path.isdir(folder):
            continue

        cmd = ["find", folder, "-type", "f", "-printf", "%T@ %A@ %C@ %i %s %u %g %m %p\\0"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)

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

        proc.wait()
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd)


def main():
    CACHE_F = "/dev/null"
    CSZE = 1024 * 1024 
    systemf = [] # all files
    xdata = [] # files to hash
    COMPLETE = [] # nsf
    SORTCOMPLETE = [] 

    COMPLETE_1 = [] # nsf perms?
    COMPLETE_2 = []
    xdata_raw = []
    diff = []

    ch = "/mnt/live/memory/images"

    collect_all_files_to_array(ch, systemf)

    layers = list(pathlib.Path(ch).glob("00[1-3]-*"))

    categories = {
        "binary": ["bin", "etc", "sbin", "usr", "opt/porteus-scripts"],
        "sects": ["etc", "home/guest", "root"],
        "library": ["lib", "lib64", "usr/lib", "usr/lib64", "var/lib"]
    }

    for category, subdirs in categories.items():
        process_category(xdata_raw, COMPLETE, layers, category, subdirs, CACHE_F, CSZE)

    systemf_set = set(systemf)
    xdata_set = set(xdata_raw)
    
    diff = systemf_set - xdata_set 

    xdata, COMPLETE_2 = process_find_lines(xdata_raw, True, "main", "sys", CACHE_F, CSZE)
    systemf, COMPLETE_1 = process_find_lines(list(diff), False, "main", "sys", CACHE_F, CSZE)

    SORTCOMPLETE = xdata + systemf

    if SORTCOMPLETE:
        return SORTCOMPLETE
    else:
        return None

if __name__ == "__main__":
    try:
        main("/dev/null")
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
