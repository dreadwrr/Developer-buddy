#!/usr/bin/env python3                  
#                                                                                                                                           09/16/2025
import glob
import hashlib
import multiprocessing
import os
from pathlib import Path
import sys
import time
import re
import processha
import psutil
import subprocess
import tempfile
import tomllib
from datetime import datetime, timedelta
import shutil
from datetime import datetime
import pstsrg
from functools import partial
from pyfunctions import green
from pyfunctions import cyan
from pyfunctions import escf_py
from pyfunctions import unescf_py
from ulink import ulink

# toml
def load_config(confdir):
    with open(confdir, 'rb') as f:
        config = tomllib.load(f)
    return config

def logic(syschg, samerlt, nodiff, diffrlt, imsg):

    if syschg:
        cyan('No sys files to report')
    if samerlt and syschg and nodiff:
        cyan('The sys search was the same as before.')
    if not diffrlt and nodiff:
        green('Nothing in the sys diff file. That is the results themselves are true.')
    if imsg:
        print(imsg)


def get_exclude_patterns(user):
    return [
        r'/var/cache',
        r'/var/run',
        r'/var/tmp',
        r'/var/lib/NetworkManager',
        r'/var/lib/upower',
        r'/var/log',
        r'/opt/porteus-scripts',
        r'/usr/share/mime',
        r'/usr/share/glib-2\.0/schemas',
        r'/usr/lib64/libXc',
        r'/usr/lib64/libudev',
        r'/var/db/sudo/lectured/1000',
        # user-specific exclusions:
        rf'/home/{re.escape(user)}/\.config/dolphinrc',
        rf'/home/{re.escape(user)}/\.config/konsolerc',
        rf'/home/{re.escape(user)}/\.config/featherpad/fp\.conf',
        r'\.config/glib-2\.0/settings/keyfile',
        r'\.bash_history',
        r'\.cache',
        r'\.dbus',
        r'\.gvfs',
        r'\.gconf',
        r'\.gnupg',
        r'\.local/share',
        r'\.xsession',
        rf'/home/{re.escape(user)}/\.config',
        r'/usr/local/save-changesnew/logs\.gpg',
        r'/usr/local/save-changesnew/recent\.gpg',
        r'/usr/local/save-changesnew/stats\.gpg',
        r'/usr/local/save-changesnew/flth\.csv',
        r'/root/\.auth',
        r'/root/\.config',
        r'/root/\.lesshst',
        r'/root/\.xauth',
    ]


def filter_lines_from_list(lines, user):
    regexes = [re.compile(p) for p in get_exclude_patterns(user)]
    filtered = [line for line in lines if not any(r.search(line) for r in regexes)]
    return filtered



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


def read_file_lines(path):
    p = Path(path)
    return [line.rstrip() for line in p.open()] if p.is_file() and p.stat().st_size > 0 else []

def timestamp_from_line(line):
    parts = line.split()
    return " ".join(parts[:2])

def parse_ts(ts):
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

def extract_quoted(line):
    m = re.search(r'"((?:[^"\\]|\\.)*)"', line)
    return m.group(1) if m else ""

def line_included(line, patterns):
    return not any(p in line for p in patterns)

def epoch_to_date(epoch):
    return datetime.fromtimestamp(float(epoch)).strftime('%Y-%m-%d %H:%M:%S')


# inotify event
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


# Parallel search and  ctime hashing
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

    return {
        "SORTCOMPLETE": {
            'modification_time': mtime,
            'access_time': atime,
            'change_time': ctime,
            'inode': inode,
            'checksum': checksum,
            'size': str(size),
            'user': user,
            'group': group,
            'mode': mode,
            'path': file_path
        }
    }


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
        if res.get("missing"):
            escaped_path = escf_py(res['file_path'])
            entry["COMPLETE"].append(
                f"Nosuchfile {res['timestamp1']} {res['timestamp2']} {escaped_path}"
            )
        else:
            # Append the entire info dict for valid files
            entry["SORTCOMPLETE"].append(res)

    return entry



def process_find_lines(lines, log_file, CACHE_F, CSZE):
    entry = process_lines(lines, CACHE_F, CSZE)
    return entry["SORTCOMPLETE"], entry["COMPLETE"]

# End parallel     


SORTCOMPLETE = [] # main results
tout = [] # ctime results
COMPLETE = [] # nsf


def main():

    noarguser=sys.argv[1] # no time
    argone=sys.argv[2] # range
    USR=sys.argv[3]
    argf=sys.argv[5] # filtered?
    dbtarget=sys.argv[6]  # the target
    flsrh=sys.argv[7]
    imsg=sys.argv[8]
    #rout=sys.argv[7]  # tmp holds action
    #tfile=sys.argv[8] # tmp file

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


   

    RECENTNUL = []  # search input
    toutnul = [] # ctime input

    filtered_lines = [] # diff file
    ABSENT = [] # diff actions
    rout = [] # all actions
    TMPOUTPUT = [] # holding   

    directories = ["/bin", "/etc", "/home", "/lib", "/lib64", "/opt", "/root", "/sbin", "/tmp", "/usr", "/var"]

    find_base_command = ['find'] + directories + ['-not', '-type', 'd', '-printf', '%T@ %A@ %C@ %i %s %u %g %m %p\0']


    config = load_config(toml)

    logSIZE = config['logs']['logSIZE']
    compLVL = config['logs']['compLVL']


    email = config['backend']['email']
    nc = config['search']['cmode'] # no compression
    turbo = config['search']['mMODE']
    ANALYTICSECT = config['analytics']['ANALYTICSECT']
    checksum = config['diagnostics']['checkSUM']
    cdiag = config['diagnostics']['cdiag']
    updatehlinks = config['diagnostics']['updatehlinks']
    ps = config['diagnostics']['POSTOP'] # proteus shield
    logpst  = config['paths']['logpst']
    statpst = config['paths']['statpst']
    pydbpst = config['paths']['pydbpst ']
    xRC = config ['search']['xRC']
   


# ##  Intst                 Loading balancing
# # Initialize core settings
# if mMODE == "mc":
#     try:
#         cores = os.cpu_count()  # Get the number of cores
#     except Exception as e:
#         cores = 1  # Default to 1 core if there's an issue
#     max_jobs = min(cores, 16)
         # Start timer



    if ANALYTICSECT == "true":
        start = time.time()

    if xRC:

        inotify_processes = [proc for proc in psutil.process_iter(['pid', 'name', 'cmdline']) if 'inotify' in proc.info['cmdline']]

        if inotify_processes:
            if log_file:

                try:
                    with open("log_file", "r") as f:
                        tout = [line.strip() for line in f if line.strip()]

                    os.remove(log_file)

                except Exception as e:
                        print(f"Error handling {log_file} file in /tmp: {e}")
            for proc in inotify_processes:
                    proc.terminate() 
            strup(log_file, CACHE_F, checksum)



    if os.path.isfile(pydbpst):
         try:
             file_size = os.stat(pydbpst).st_size       
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
                nc = "true"
#             elif file_size == 0:
#                 print(f"{logpst} is 0 bytes. To resume persistent logging, delete the file")
#                 STATPST = "false"
         except Exception as e:
             print(f"Error checking or modifying log file: {e}")


    TEMPDIR = tempfile.mkdtemp()
    tfile=TEMPDIR + ' ' + 'tmpd'

    if argone != "noarguser" and argone != "":
        try:
            argone = int(argone)
            p = 60
            tmn = argone / p
            if argone % p == 0:
                tmn = argone // p
            cyan(f"Searching for files {argone} seconds old or newer")

        except ValueError:
            print(f"{sys.argv[2]} is not an integer. Proceeding with non-integer logic.")
            
            argone = ".txt"
            
            if len(sys.argv) > 4:
                directory = sys.argv[4]
                if not os.path.isdir(directory):
                    print(f'Invalid argument {sys.argv[4]}. PWD required.')
                    sys.exit(1)
                os.chdir(directory)
            
            filename = sys.argv[2]
            if not os.path.isfile(filename) and not os.path.isdir(filename):
                print('No such directory, file, or integer.')
                sys.exit(1)

            parseflnm = os.path.basename(filename)
            if parseflnm == "":
                parseflnm = filename.rstrip('/').split('/')[-1]

            cyan(f"Searching for files newer than {filename}")

            flsrh = "true"
            #feed_file = "RECENTNUL"  # Array
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

        def gettime(valo, valt=0):
            if ANALYTICSECT:
                valo = time.time()
                if checksum == "true":
                    valt = time.time()     
            return valo, valt   

        if not tout: # is there xRC?

            find_command_mmin = find_base_command + [mmin]
            find_command_cmin = find_base_command + [cmin]

            mmin_lines = subprocess.run(find_command_mmin, capture_output=True, text=True, check=True)
            cmin_lines = subprocess.run(find_command_cmin, capture_output=True, text=True, check=True)

            end, cstart = gettime(start, cstart)

            toutnul = cmin_lines.stdout.splitlines()
            tout, COMPLETE_2 = process_find_lines(toutnul, CACHE_F, CSZE)

        else:

            find_command_mmin = find_base_command + [mmin]

            mmin_lines = subprocess.run(find_command_mmin, capture_output=True, text=True, check=True)

            end, cstart = gettime(start, cstart)

        RECENTNUL = mmin_lines.stdout.splitlines()
        SORTCOMPLETE, COMPLETE_1 = process_find_lines(RECENTNUL, CACHE_F, CSZE)

        if ANALYTICSECT:
            cend = time.time()

        COMPLETE = COMPLETE_1 + COMPLETE_2

        if os.getenv("FEEDBACK") == "true": # scrolling terminal look
            for file_info in RECENTNUL:
                print(file_info['path'])

    
        exclude_patterns = [
        r"/usr/local/save-changesnew/flth\.csv",
        rf"/home/{USR}/Downloads/rnt",
        logpst,
        statpst,
        pydbpst
    ]

    lines = read_file_lines(SORTCOMPLETE)
    lines = sorted(set(lines), key=lambda l: parse_ts(timestamp_from_line(l)))

    SRTTIME = timestamp_from_line(lines[0]) if lines else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PRD = SRTTIME


    lines += [l for l in tout if timestamp_from_line(l) >= PRD]

    # Apply exclusion filter
    lines = [l for l in lines if line_included(l, exclude_patterns)]
    lines = sorted(set(lines), key=lambda l: parse_ts(timestamp_from_line(l)))


    if updatehlinks == "true":
        green('Updating hardlinks')
        TMPOPT = ulink(SORTCOMPLETE, LCLMODULENAME, 'true') 


    if flsrh == "false" or flsrh == "rnt":
        start_dt = parse_ts(SRTTIME)
        range_sec = 300 if noarguser == 'noarguser' else int(argone)
        end_dt = start_dt + timedelta(seconds=range_sec)
        lines = [l for l in lines if parse_ts(timestamp_from_line(l)) <= end_dt]


    timestamps = [timestamp_from_line(l) for l in lines]
    quoted_strings = [extract_quoted(l) for l in lines]
    combined_all = [f"{ts} {q}" for ts, q in zip(timestamps, quoted_strings)]


    TMPOUTPUT = []
    for line in lines:
        quoted_match = re.search(r'"((?:[^"\\]|\\.)*)"', line)
        if not quoted_match:
            continue
        filepath = quoted_match.group(1)
        escaped_path = escf_py(filepath)

        line_without_file = line.replace(quoted_match.group(0), '').strip()
        other_fields = line_without_file.split()
        if len(other_fields) < 2:
            continue
        field1 = other_fields[0]
        field2 = other_fields[1]
        TMPOUTPUT.append(f"{field1} {field2} {escaped_path}")


    tmp_lines = [l for l in TMPOUTPUT if l.split(" ", 2)[2].startswith("/tmp")]
    tmparr_non_tmp = [l for l in TMPOUTPUT if not l.split(" ", 2)[2].startswith("/tmp")]

    TMPOUTPUT = tmp_lines 


    if flsrh != "rnt":  # 'recentchanges search'
        SORTCOMPLETE = [l for l in lines if not extract_quoted(l).startswith("/tmp")]
        TMPOPT = tmparr_non_tmp
    else:  # 'recentchanges'
        SORTCOMPLETE = lines
        TMPOPT = TMPOUTPUT


    RECENT = TMPOPT[:]


    if argf == "filtered" or flsrh == "true":
        logf = TMPOPT
        if argf == "filtered" and flsrh == "true":
            logf = RECENT
        TMPOPT = filter_lines_from_list(TMPOPT, user=USR)  # Apply filter


    #Merge/Move
    if os.path.getsize(SORTCOMPLETE) > 0:
        if flsrh:
            flnm = f'xNewerThan_{parseflnm}{argone}'
            flnmdff = f'xDiffFromLast_{parseflnm}{argone}'
        elif flsrh == "filtered":
            flnm = f'xFltchanges_{argone}'
            flnmdff = f'xFltDiffFromLastSearch_{argone}'
        else:
            flnm = f'xSystemchanges{argone}'
            flnmdff = f'xSystemDiffFromLastSearch{argone}'

        filepath = os.path.join(USRDIR, f'{MODULENAME}{flnm}')
        filedata = []

        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                OLDSORT = f.readlines()

        if not OLDSORT and not flsrh and flsrh != "filtered":
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

                    if filedata:
                        break 

        # Reset
        clear_logs(USRDIR, MODULENAME)

        # /tmp results to user
        if os.path.exists(TMPOUTPUT) and os.path.getsize(TMPOUTPUT) > 0:
            target_filename = f"{MODULENAME}xSystemTmpfiles{parseflnm}{argone.replace('.txt', '')}"
            target_path = os.path.join(USRDIR, target_filename)
            with open(TMPOUTPUT, 'r') as src, open(target_path, 'w') as dst:
                dst.write(src.read())
                # If chown needed, uncomment:
                # import pwd
                # uid = pwd.getpwnam(USR).pw_uid
                # os.chown(target_path, uid, -1)

        # Diff file
        if OLDSORT:

            filedata = [line.strip() for line in OLDSORT]
            sortcomplete_stripped = [line.strip() for line in TMPOPT]

            difffile=f'{USRDIR}{MODULENAME}{flnmdff}'
            filtered_lines = [line for line in filedata if line not in sortcomplete_stripped]

            if filtered_lines:
                nodiff = True
                with open(difffile, 'w') as f:
                    for line in filtered_lines:
                        f.write(line + '\n')
            else:
                samerlt = True

        
        # Output search results to user
        with open(filepath, 'w') as f:
            f.write("\n".join(SORTCOMPLETE) + "\n")


        tmpopt_paths = set(line.strip().split(" ", 2)[-1] for line in TMPOPT)

        for line in filtered_lines:
            parts = line.strip().split(" ", 2)
            if len(parts) < 3:
                continue  # Skip malformed lines

            timestamp_str, user, filepath = parts

            if parse_ts(timestamp_str) < start_dt:
                continue  # Skip lines older than the threshold

            if filepath in tmpopt_paths:
                ABSENT.append(f"Modified {line}")
            else:
                ABSENT.append(f"Deleted {line}")
                rout.append(f"Deleted {timestamp_str} {line}")
    
    if COMPLETE:
        rout.extend(COMPLETE)


    # Backend
    pstsrg(SORTCOMPLETE, dbtarget, rout, tfile, checksum, cdiag, email, turbo, ANALYTICSECT, ps, nc)
    processha(rout, ABSENT, difffile, cerr, TMPOPT, flsrh, )

# Pass off to bash. or not

    if ANALYTICSECT:
        el = end - start  
        print(f'Search took {el:.3f} seconds')
        if checksum:
            el = cend - cstart
            print(f'Checksum took {el:.3f} seconds')

    if flsrh == "true":
        cyan(f'All files newer than{filename} in /Downloads')
    elif argf:
        cyan('All new filtered files are listed in /Downloads')

    else:
        cyan('All new system files are listed in /Downloads')

    os.rmdir(TEMPDIR)
    logic(syschg, samerlt, nodiff, diffrlt, imsg)
    

    # Open notepad













    




















# ##  Intst



# # Initialize core settings
# if mMODE == "mc":
#     try:
#         cores = os.cpu_count()  # Get the number of cores
#     except Exception as e:
#         cores = 1  # Default to 1 core if there's an issue
#     max_jobs = min(cores, 16)

# # Check if xRC is "true" and handle inotify
# if xRC == "true":
#     # Check if inotify is running using psutil (alternative to pgrep)
#     inotify_processes = [proc for proc in psutil.process_iter(['pid', 'name', 'cmdline']) if 'inotify' in proc.info['cmdline']]
    
#     if inotify_processes:
#         if log_file:
#             # Copy log file to tout if inotify is running
#             try:
#                 with open(log_file, 'r') as logf:
#                     log_data = logf.read()
#                 with open(tout, 'w') as toutf:
#                     toutf.write(log_data)
                
#                 # Kill inotifywait process and clean up log
#                 for proc in inotify_processes:
#                     proc.terminate()  # Terminates the inotify process
                
#                 os.remove(log_file)
#                 strup()  # Assuming strup() is another function you're using to reset or start something
#             except Exception as e:
#                 print(f"Error handling log file: {e}")
#         else:
#             strup()
#     else:
#         strup()

# # Check if STATPST is "true" and manage log size for persistent logging
# if STATPST == "true":
#     if os.path.isfile(logpst):
#         try:
#             file_size = os.stat(logpst).st_size  # Get file size in bytes
            
#             if file_size // 1048576 > logSIZE:  # Convert to MB and check against logSIZE
#                 if logPRF == "del":
#                     open(logpst, 'w').close()  # Clear the file
#                 elif logPRF == "stop":
#                     print("persist log saving stopped on size limit")
#                 STATPST = "false"
                
#                 if logPRF == "rfh":
#                     os.remove(logpst)
#                     STATPST = "true"
#             elif file_size // 1048576 >= compLVL:  # If file size exceeds compLVL, set nc to true
#                 nc = "true"
#             elif file_size == 0:
#                 print(f"{logpst} is 0 bytes. To resume persistent logging, delete the file")
#                 STATPST = "false"
#         except Exception as e:
#             print(f"Error checking or modifying log file: {e}")