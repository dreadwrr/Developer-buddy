#!/usr/bin/env python3                  
#!/bin/bash
#   NMS5                                                                            09/16/2025  v3.0
#   recentchanges. Developer buddy      make xzm
#   Provide ease of pattern finding ie what files to block we can do this a number of ways
#   1) if a file was there (many as in more than a few) and another search lists them as deleted its either a sys file or not but unwanted nontheless
#   2) Is a system file inherent to the specifc platform
#   3) intangibles ie trashed items that may pop up infrequently and are not known about
#
#  The purpose of this script is to save files ideally less than 5 minutes old. So when compiling or you dont know where some files are
#or what changed on your system. So if you compiled something you call this script to build a module of it for distribution.
#  If not using for developing call it a file change snapshot
#  We use the find command to list all files 5 minutes or newer. Filter it and then get to copying the files in a temporary staging directory.
#  Then take those files and make an .xzm. It will be placed in   /tmp  along with a transfer log to staging directory and file manifest of the xzm
#
#  recentchanges command from    /usr/bin/recentchanges
#  Also borred script features from various scripts on porteus forums
# working off of base save-changes script by
# Author: Brokenman <brokenman@porteus.org>
# Author: fanthom <fanthom@porteus.org>
import glob
import hashlib
import multiprocessing
import os
import re
import sys
import time
import processha
import pstsrg
import psutil
import pwd
import subprocess
import tempfile
import tomllib
from datetime import datetime, timedelta
from datetime import datetime
from filter import get_exclude_patterns
from filterhits import update_filter_csv
from functools import partial
from pathlib import Path
from processha import filter_output
from pyfunctions import green
from pyfunctions import cyan
from pyfunctions import escf_py
from pyfunctions import parse_datetime
from ulink import ulink

# toml
def load_config(confdir):
    with open(confdir, 'rb') as f:
        config = tomllib.load(f)
    return config


def logic(syschg, samerlt, nodiff, diffrlt, MODULENAME, THETIME, argone, argf, filename, flsrh, imsg, method):
    
    if method == "rnt":
        if THETIME != "noarguser" and syschg:
            cyan("All system files in the last $THETIME seconds are included")
            
            cyan(f'{MODULENAME}xSystemchanges{argone}')
        elif syschg:
            cyan("All system files in the last 5 minutes are included")

            cyan(f'{MODULENAME}xSystemchanges{argone}')
    else:
        if flsrh:
            cyan(f'All files newer than{filename} in /Downloads')
        elif argf:
            cyan('All new filtered files are listed in /Downloads')
        else:
            cyan('All new system files are listed in /Downloads')

        if syschg:
            cyan('No sys files to report')
        if samerlt and syschg and nodiff:
            cyan('The sys search was the same as before.')
        if not diffrlt and nodiff:
            green('Nothing in the sys diff file. That is the results themselves are true.')
        if imsg:
            print(imsg)


def display(dspEDITOR, USRDIR, MODULENAME, flnm):
    if dspEDITOR != "false":
        filepath = os.path.join(USRDIR, f'{MODULENAME}{flnm}')
        if dspEDITOR == "xed":
            if os.path.isfile("/usr/bin/xed"):
                subprocess.Popen(["xed", filepath])
            else:
                print(f'{dspEDITOR} not installed')
        if dspEDITOR == "featherpad":
            if os.path.isfile("/usr/bin/xed"):
                subprocess.Popen([dspEDITOR, filepath])
            else:
                print(f'{dspEDITOR} not installed')

# filter.py
def filter_lines_from_list(lines, user):
    regexes = [re.compile(p) for p in get_exclude_patterns(user)]
    filtered = [line for line in lines if not any(r.search(line) for r in regexes)]
    return filtered

#inclusions
def get_runtime_exclude_list(USR, logpst, statpst, dbtarget):
    return [
        "/usr/local/save-changesnew/flth.csv",
        f"/home/{USR}/Downloads/rnt",
        logpst,
        statpst,
        dbtarget
    ]

def gettime(analytic=False, checksum=False, init="false", x=0, y=0):
    if analytic:
        x = time.time()
        if checksum:
            
            y = time.time()
            if init == "init":
                cyan('Running checksum.')
    return x, y

# 'recentchanges search'
def clear_logs(USRDIR, MODULENAME):
    suffixes = [
    "xSystemDiffFromLastSearch",
    "xFltDiffFromLastSearch",
    "xFltchanges",
    "xFltTmp",
    "xSystemchanges",
    "xSystemTmp",
    "xNewerThan",
    "xDiffFromLast"
]
    for suffix in suffixes:
        pattern = os.path.join(USRDIR, MODULENAME.lstrip("/")) + suffix
        for filename in os.listdir(USRDIR):
            if filename.startswith(MODULENAME.lstrip("/")) and suffix in filename:
                try:
                    os.remove(os.path.join(USRDIR, filename))
                except FileNotFoundError:
                    continue

#init

def intst(dbtarget, logSIZE, CSZE, compLVL):
    if os.path.isfile(dbtarget):
        try:
            file_size = os.stat(dbtarget).st_size       
            if file_size // CSZE > logSIZE: 
                print('db exceeding size limit')
#                 if logPRF == "del":
#                     open(logpst, 'w').close()  # Clear the file
#                 elif logPRF == "stop":
#                     print("persist log saving stopped on size limit")
#                 STATPST = "false"            
#                 if logPRF == "rfh":
#                     os.remove(logpst)
#                     STATPST = "true"
            elif file_size // CSZE >= compLVL:  # If file size exceeds compLVL, set nc to true
                return True
#             elif file_size == 0:
#                 print(f"{logpst} is 0 bytes. To resume persistent logging, delete the file")
#                 STATPST = "false"
            return False
        except Exception as e:
            print(f"Error checking or modifying log file: {e}")


## parsing python
def read_file_lines(path):
    p = Path(path)
    return [line.rstrip() for line in p.open()] if p.is_file() and p.stat().st_size > 0 else []

def timestamp_from_line(line):
    parts = line.split()
    return " ".join(parts[:2])

def extract_quoted(line):
    m = re.search(r'"((?:[^"\\]|\\.)*)"', line)
    return m.group(1) if m else ""

def line_included(line, patterns):
    return not any(p in line for p in patterns)

def epoch_to_date(epoch):
    return datetime.fromtimestamp(float(epoch)).strftime('%Y-%m-%d %H:%M:%S')


# inotify event xRC
def strup(log_file, cache_f, checksum):
    cmd = [
        "/usr/local/save-changesnew/start_inotify",
        log_file,
        cache_f,
        checksum,
        "ctime",
        "3600"
    ]
    subprocess.run(cmd, check=True)


# Parallel SORTCOMPLETE search and  ctime hashing
#
def calculate_checksum(file_path):
    try:
        hash_func = hashlib.md5()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        return None
    
def upt_cache(CACHE_F, inode, size, mtime, checksum, path):
    with open(CACHE_F, "a") as f:
        f.write(f"{inode}|{size}|{mtime} {checksum} {path}\n")

def get_cached(CACHE_F, inode, size, mtime):
    key = f"{inode}|{size}|{mtime}"
    if not os.path.exists(CACHE_F):
        return None
    with open(CACHE_F, "r") as f:
        for line in f:
            if line.startswith(key + " "):
                parts = line.strip().split(" ", 2)
                if len(parts) >= 2:
                    return parts[1]  # checksum
    return None

def process_line(line, CACHE_F, CSZE):
    parts = line.split('\0')
    if len(parts) < 9:
        return None

    mod_time, access_time, change_time, inode, size, user, group, mode, file_path = parts[:9]
    size = int(size)

    if not os.path.exists(file_path):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "COMPLETE": f"Nosuchfile {now_str} {now_str} {file_path}"
        }

    if size > CSZE:
        checksum = get_cached(CACHE_F, inode, size, mod_time)
        if checksum is None:
            checksum = calculate_checksum(file_path)
            upt_cache(inode, size, mod_time, checksum, file_path, CACHE_F)
    else:
        checksum = calculate_checksum(file_path)

    mtime = epoch_to_date(mod_time)
    atime = epoch_to_date(access_time)
    ctime = epoch_to_date(change_time)

    return (
            mtime,
            atime,
            ctime,
            inode,
            checksum,
            str(size),
            user,
            group,
            mode,
            file_path
    )
    

def process_lines(lines, CACHE_F, CSZE):
    worker = partial(process_line, CACHE_F=CACHE_F, CSZE=CSZE)
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        results = pool.map(worker, lines)

    entry = {
        "SORTCOMPLETE": [],
        "COMPLETE": []
    }

    for res in results:
        if res is None:
            continue
        if "COMPLETE" in res:
            parts = res["COMPLETE"].split()
            if len(parts) >= 4:
                parts[-1] = escf_py(parts[-1])
                res["COMPLETE"] = " ".join(parts)
            entry["COMPLETE"].append(res["COMPLETE"])
        elif "SORTCOMPLETE" in res:
            entry["SORTCOMPLETE"].append(res["SORTCOMPLETE"])

    return entry



def process_find_lines(lines, CACHE_F, CSZE):
    entry = process_lines(lines, CACHE_F, CSZE)
    return entry["SORTCOMPLETE"], entry["COMPLETE"]
                                                                                            #
                                                                    #End parallel #    

def openrc(log_file, CACHE_F, checksum, tout):
    inotify_processes = [proc for proc in psutil.process_iter(['pid', 'name', 'cmdline']) if 'inotify' in proc.info['cmdline']]

    if inotify_processes:
        if log_file:

            try:
                with open(log_file, "r") as f:
                    tout = [line.strip() for line in f if line.strip()]

                os.remove(log_file)

            except Exception as e:
                print(f"Error handling {log_file} file in /tmp: {e}")

        for proc in inotify_processes:
                proc.terminate() 
                exit_code = proc.poll()
                if exit_code is not None:
                    strup(log_file, CACHE_F, checksum)
    return tout


def main():

    THETIME=sys.argv[1]
    method=sys.argv[6]

    if THETIME != 'search' and method != "rnt":
        print('exiting not a search')
        sys.exit(0)     

    RECENTNUL = []  # search input
    toutnul = [] # ctime input
    SORTCOMPLETE = [] # main results
    tout = [] # ctime results
    COMPLETE = [] # nsf

    difff_file = [] # diff file
    ABSENT = [] # diff file actions
    rout = [] # all actions from ha

    TMPOUTPUT = [] # holding   


    argone=sys.argv[2] # range
    USR=sys.argv[3]
    pwrd=sys.argv[4]
    argf=sys.argv[5] # filtered?  
    imsg=sys.argv[7]

    CSZE = 1024 * 1024  # >= 1MB in bytes to cache

    diffrlt = False
    samerlt = False
    nodiff = False
    syschg = False



    chxzm="/rntfiles.xzm"
    filename = os.path.basename(chxzm)  
    LCLMODULENAME = os.path.splitext(filename)[0]
    MODULENAME= os.path.splitext(chxzm)[0]
    USRDIR =  f'/home/{USR}/Downloads'    

    log_file="/tmp/file_creation_log.txt"
    flth="/usr/local/save-changesnew/flth.csv"
    CACHE_F="/tmp/ctimecache"
    slog="/tmp/scr"
    cerr="/tmp/cerr"
    toml="/usr/local/save-changesnew/config.toml"

    fmt="%Y-%m-%d %H:%M:%S"

    directories = ["/bin", "/etc", "/home", "/lib", "/lib64", "/opt", "/root", "/sbin", "/tmp", "/usr", "/var"]

    find_base_command = ['find'] + directories + ['-not', '-type', 'd', '-printf', '%T@ %A@ %C@ %i %s %u %g %m %p\0']

    config = load_config(toml)

    FEEDBACK = config['analytics']['ANALYTICS']
    ANALYTICSECT = config['analytics']['ANALYTICSECT']

    logSIZE = config['logs']['logSIZE']
    compLVL = config['logs']['compLVL']
    dspEDITOR = config['display']['dspEDITOR']

    email = config['backend']['email']
    
    checksum = config['diagnostics']['checkSUM']
    cdiag = config['diagnostics']['cdiag']
    supbrw = config['diagnostics']['supbrw']
    supress = config['diagnostics']['supress']
    ps = config['diagnostics']['POSTOP'] # proteus shield
    updatehlinks = config['diagnostics']['updatehlinks']

    logpst  = config['paths']['logpst'] # for inclusions
    statpst = config['paths']['statpst']
    dbtarget = config['paths']['dbtarget']

    nc = config['search']['cmode'] # no compression
    turbo = config['search']['mMODE']
    xRC = config ['search']['xRC']
   

    start = gettime(ANALYTICSECT, start)

    if xRC:
        tout = openrc(log_file, CACHE_F, checksum, tout)

    nc=intst(dbtarget, logSIZE, CSZE, compLVL)

    TEMPDIR = tempfile.mkdtemp()
    #tfile=TEMPDIR + '/' + 'tmpd'


    if argone != "noarguser" and argone != "":
        try:
            argone = int(argone)
            p = 60
            tmn = argone / p
            if argone % p == 0:
                tmn = argone // p
            cyan(f"Searching for files {argone} seconds old or newer")

        except ValueError: # its a file search
            print(f"{sys.argv[2]} is not an integer. Proceeding with non-integer logic.")
            argone = ".txt"
            if not os.path.isdir(pwrd):
                print(f'Invalid argument {sys.argv[4]}. PWD required.')
                sys.exit(1)
            os.chdir(pwrd)
        
            filename = sys.argv[2]
            if not os.path.isfile(filename) and not os.path.isdir(filename):
                print('No such directory, file, or integer.')
                sys.exit(1)

            parseflnm = os.path.basename(filename)
            if parseflnm == "":
                parseflnm = filename.rstrip('/').split('/')[-1]

            cyan(f"Searching for files newer than {filename}")

            flsrh = "true"
            ct = int(time.time())
            fmt = int(os.stat(filename).st_mtime)
            ag = ct - fmt
            mmin = f'-newer {filename}'
            cmin = f'-cmin -{ag}'

    else:
        argone = 5
        tmn = argone
        cyan('Searching for files 5 minutes old or newer')

    if tmn:
        logf=RECENT
        mmin = f'-mmin -{tmn}'
        cmin = f'-cmin -{tmn}'



    if not tout: # is there xRC? if not both mtime and ctime (toutnul)

        find_command_mmin = find_base_command + [mmin]
        find_command_cmin = find_base_command + [cmin]

        mmin_lines = subprocess.run(find_command_mmin, capture_output=True, text=True, check=True)
        cmin_lines = subprocess.run(find_command_cmin, capture_output=True, text=True, check=True)
        cstart = 0  # Initialize cstart to avoid UnboundLocalError
        end, cstart = gettime(ANALYTICSECT, checksum, start, cstart)
        toutnul = cmin_lines.stdout.splitlines()

        tout, COMPLETE_2 = process_find_lines(toutnul, CACHE_F, CSZE) # ctime > mtime files

    # bypass 1 loop
    else:

        find_command_mmin = find_base_command + [mmin]
        cstart = 0
        end, cstart = gettime(ANALYTICSECT, checksum, "init", start, cstart)
        end, cstart = gettime(ANALYTICSECT, checksum, "init", start, cstart)

    RECENTNUL = mmin_lines.stdout.splitlines()

    SORTCOMPLETE, COMPLETE_1 = process_find_lines(RECENTNUL, CACHE_F, CSZE) # main files
    cend = gettime(ANALYTICSECT, cend)

    COMPLETE = COMPLETE_1 + COMPLETE_2 # nsf

    if FEEDBACK: # scrolling terminal look
        for file_info in RECENTNUL:
            print(file_info)


    parsed_lines = []
    for l in SORTCOMPLETE:
        ts = parse_datetime(timestamp_from_line(l), fmt)
        if ts:
            parsed_lines.append((ts, l))


    parsed_lines.sort(key=lambda x: x[0])

    SRTTIME = timestamp_from_line(parsed_lines[0][1]) if parsed_lines else datetime.now().strftime(fmt)
    PRD = SRTTIME
    parsed_PRD = parse_datetime(PRD, fmt)

    for l in tout:
        ts = parse_datetime(timestamp_from_line(l), fmt)
        if ts and ts >= parsed_PRD:
            parsed_lines.append((ts, l))

    seen = set()
    unique_lines = []
    for ts, line in parsed_lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append((ts, line))

    exclude_patterns = get_runtime_exclude_list(USR, logpst, statpst, dbtarget)
    filtered_lines = [line for ts, line in unique_lines if line_included(line, exclude_patterns)]

    if updatehlinks :
        green('Updating hardlinks')
        SORTCOMPLETE = ulink(SORTCOMPLETE, LCLMODULENAME, supbrw)


    if flsrh == "false" or flsrh == "rnt":
        start_dt = parse_datetime(SRTTIME, fmt)
        range_sec = 300 if argone == 'noarguser' else int(argone)
        end_dt = start_dt + timedelta(seconds=range_sec)
        lines = [l for ts, l in unique_lines if parse_datetime(timestamp_from_line(l), fmt) <= end_dt]


    TMPOUTPUT = []

    for line in filtered_lines:
        quoted_match = re.search(r'"((?:[^"\\]|\\.)*)"', line)
        if not quoted_match:
            continue
        filepath = quoted_match.group(1)
        escaped_path = escf_py(filepath)

        parts = line.strip().split()
        if len(parts) < 2:
            continue

        ts_str = f"{parts[0]} {parts[1]}"

        TMPOUTPUT.append(f"{ts_str} {escaped_path}")


    tmp_lines = [l for l in TMPOUTPUT if l.split(" ", 2)[2].startswith("/tmp")]
    non_tmp_lines = [l for l in TMPOUTPUT if not l.split(" ", 2)[2].startswith("/tmp")]


    if method != "rnt":  # 'recentchanges search'
        SORTCOMPLETE = [l for l in lines if not extract_quoted(l).startswith("/tmp")]
        TMPOPT = non_tmp_lines
    else:  # 'recentchanges'
        SORTCOMPLETE = lines
        TMPOPT = tmp_lines  # only /tmp files


    RECENT = TMPOPT[:]


    if argf == "filtered" or flsrh:
        logf = TMPOPT # filter the search
        if argf == "filtered" and flsrh:
            logf = RECENT # dont filter the search

        TMPOPT = filter_lines_from_list(TMPOPT, USR)  # Apply filter



   # Copy logic re changes .xzm
    try:
        result = subprocess.run(
            ['/usr/local/save-changesnew/recentchanges', THETIME, argone, USR],
            capture_output=True,
            text=True
        )

        if result.returncode == 7:
            cyan("There were no files to grab.")
        elif result.returncode != 0:
            print(f'/rntfiles.xzm failed to unable to make xzm. {result.returncode}')
            print("STDERR:", result.stderr)
        else:
            cyan(result)

    except Exception as e:
        print(f"Error running script: {e}")


    #Merge/Move
    if SORTCOMPLETE:
        OLDSORT = []
        if flsrh:
            flnm = f'xNewerThan_{parseflnm}{argone}'
            flnmdff = f'xDiffFromLast_{parseflnm}{argone}'
        elif argf == "filtered":
            flnm = f'xFltchanges_{argone}'
            flnmdff = f'xFltDiffFromLastSearch_{argone}'
        else:
            flnm = f'xSystemchanges{argone}'
            flnmdff = f'xSystemDiffFromLastSearch{argone}'

        filepath = os.path.join(USRDIR, f'{MODULENAME}{flnm}')

        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                OLDSORT = f.readlines()

        if not OLDSORT and not flsrh and argf != "filtered":
            fallback_path = f'/tmp/{MODULENAME}{flnm}'
            if os.path.exists(fallback_path):
                with open(fallback_path, 'r') as f:
                    OLDSORT = f.readlines()

            if not OLDSORT:
                    folders = sorted(glob.glob(f'/tmp/{MODULENAME}_MDY*'), reverse=True)

                    for folder in folders:
                        pattern = os.path.join(folder, f"{MODULENAME}xSystemchanges{argone}*")
                        matching_files = sorted(glob.glob(pattern), reverse=True)

                        for file in matching_files:
                            if os.path.isfile(file):
                                with open(file, 'r') as f:
                                    OLDSORT = f.readlines()
                                break 

                        if OLDSORT:
                            break 

        # Reset
        clear_logs(USRDIR, MODULENAME)

        # /tmp results to user
        if TMPOUTPUT:  # only proceed if the list is not empty
            # Handle argone filename modifications
            base_argone = argone.replace('.txt', '') if argone.endswith('.txt') else argone
            target_filename = f"{MODULENAME}xSystemTmpfiles{parseflnm}{base_argone}"
            target_path = os.path.join(USRDIR, target_filename)

            # Write the list to the file
            with open(target_path, 'w') as dst:
                dst.write('\n'.join(TMPOUTPUT) + '\n')  # join lines with newlines

            # Set ownership
            import pwd, os
            uid = pwd.getpwnam(USR).pw_uid
            os.chown(target_path, uid, -1)

        # Diff file
        if OLDSORT:

            toutnul = [line.strip() for line in OLDSORT]
            sortcomplete_stripped = [line.strip() for line in logf]

            diffnm=f'{USRDIR}{MODULENAME}{flnmdff}'
            difff_file = [line for line in toutnul if line not in sortcomplete_stripped]

            if difff_file:
                nodiff = True
                with open(diffnm, 'w') as f:
                    for line in difff_file:
                        f.write(line + '\n')
            else:
                samerlt = True

        
            # Output search result SORTCOMPLETE to user
            with open(filepath, 'w') as f:
                f.write("\n".join(SORTCOMPLETE) + "\n")
            uid = pwd.getpwnam(USR).pw_uid
            os.chown(filepath, uid, -1)


            tmpopt_paths = set(line.strip().split(" ", 2)[-1] for line in TMPOPT)

            for line in difff_file:
                parts = line.strip().split(" ", 2)
                if len(parts) < 3:
                    continue

                timestamp_str = parts[0] + " " + parts[1]
                filepath = parts[2]

                if parse_datetime(timestamp_str, fmt) < start_dt:
                    continue

                if filepath in tmpopt_paths:
                    ABSENT.append(f"Modified {line}")
                else:
                    ABSENT.append(f"Deleted {line}")
                    rout.append(f"Deleted {timestamp_str} {line}")
    

    # Backend
    pstsrg.main(SORTCOMPLETE, COMPLETE, dbtarget, rout, checksum, cdiag, email, turbo, ANALYTICSECT, ps, nc, USR)
    csum=processha(rout, ABSENT, diffnm, cerr, TMPOPT, flsrh, LCLMODULENAME, argf, USR, supbrw, supress)
    
    update_filter_csv(TMPOPT, USR, flth)


    if not csum and os.path.exists(slog) and supress:
        with open(slog, 'r') as src, open(diffnm, 'a') as dst:
            dst.write(f"\ncdiag\n")
            dst.write(src.read())

    elif not csum and not supress and os.path.exists(slog):
        filter_output(slog, LCLMODULENAME, 'Checksum', 'no', 'blue', 'yellow', 'scr')
        with open(slog, 'r') as src, open(diffnm, 'a') as dst:
            dst.write(f"\ncdiag\n")
            dst.write(src.read())

    elif csum:
        with open(cerr, 'r') as src, open(diffnm, 'a') as dst:
            dst.write(f"\ncdiag alert\n")
            dst.write(src.read())

    if os.path.exists(diffnm):
        uid = pwd.getpwnam(USR).pw_uid
        os.chown(diffnm, uid, -1)

    if ANALYTICSECT:
        el = end - start  
        print(f'Search took {el:.3f} seconds')
        if checksum:
            el = cend - cstart
            print(f'Checksum took {el:.3f} seconds')


    #cleanup
    import shutil
    try:
        shutil.rmtree(TEMPDIR)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Error removing temporary directory {TEMPDIR}: {e}")

    logic(syschg, samerlt, nodiff, diffrlt, MODULENAME, THETIME, argone, argf, filename, flsrh, imsg)
    display(dspEDITOR, USRDIR, MODULENAME, flnm)

