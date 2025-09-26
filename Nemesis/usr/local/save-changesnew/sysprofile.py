# 09/26/2025 proteus shield sys profile
import subprocess
import os
import sys
from fsearch import process_find_lines

def process_layer(RECENT, tout, layer, subdirs, CACHE_F, CSZE, match_args=None):

    for subdir in subdirs:
        dir_path = os.path.join(layer, subdir)
        if not os.path.isdir(dir_path):
            continue

        cmd = ["find", dir_path, "-type", "f"]
        if match_args:
            cmd += match_args
        cmd += ["-printf", "%T@ %A@ %C@ %i %s %u %g %m %p\\0"]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        output, _ = proc.communicate()

        if proc.returncode  != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd)

        file_entries = [entry.decode() for entry in output.split(b'\0') if entry]

        RECENT, tout = process_find_lines(file_entries, "true", "mtime", "sys", CACHE_F, CSZE)
    return RECENT, tout


def process_category(RECENT, tout, layers, category, subdirs, CACHE_F, CSZE):
    for layer in layers:
        

        dirname = os.path.basename(str(layer))

        if dirname.startswith("000"): # dont hash kernel firmware
            continue

        match_args = []
        if category == "binary":
            match_args = ["-executable"]
        elif category == "library":
            match_args = ["-name", "*.so*"]

        RECENT, tout = process_layer(RECENT, tout, str(layer), category, subdirs, CACHE_F, CSZE, match_args)
    return RECENT, tout


def main():
    import pathlib

    CACHE_F = sys.argv[1] # cache file
    CSZE = 1024 * 1024 # cache size boundary

    systemf = [] # all files
    xdata = [] # profile files
    COMPLETE = [] # nsf
    SORTCOMPLETE = [] # complete system profile

    diff = [] # comm -23

    ch = "/mnt/live/memory/images"


    def collect_all_files_to_array(ch_base):
        layers = [f"{ch_base}{str(i).zfill(3)}" for i in range(4)]
        layers += list(pathlib.Path(ch_base).glob("00[0-3]-*"))

        all_entries = []
        for folder in layers:
            folder = str(folder)
            if not os.path.isdir(folder):
                continue

            cmd = ["find", folder, "-type", "f", "-printf", "%T@ %A@ %C@ %i %s %u %g %m %p\0"]
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
                        all_entries.append(part.decode("utf-8", errors="replace"))

            if buffer.strip():
                all_entries.append(buffer.decode("utf-8", errors="replace"))

            proc.wait()
            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, cmd)

        return all_entries

    systemf = collect_all_files_to_array(ch)

    layers += list(pathlib.Path(ch).glob("00[1-3]-*"))

    categories = {
        "binary": ["bin", "etc", "sbin", "usr", "opt/porteus-scripts"],
        "sects": ["etc", "home/guest", "root"],
        "library": ["lib", "lib64", "usr/lib", "usr/lib64", "var/lib"]
    }


    for category, subdirs in categories.items():
        xdata, COMPLETE = process_category(xdata, COMPLETE, layers, category, subdirs, CACHE_F, CSZE)



    systemf_set = set(systemf)
    xdata_set = set([item[1] for item in xdata]) 

    diff = systemf_set - xdata_set


    REMAINING, _ = process_find_lines(diff, "false", "mtime", "sys", CACHE_F, CSZE)


    SORTCOMPLETE = xdata+ REMAINING

    return SORTCOMPLETE

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
