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

import pwd
import shutil
import subprocess
import tempfile

from datetime import datetime, timedelta
from datetime import datetime

from filterhits import update_filter_csv
from functools import partial
from pathlib import Path
from processha import isdiff
from processha import filter_output

from rntchangesfunctions import clear_logs
from rntchangesfunctions import display
from rntchangesfunctions import filter_lines_from_list
from rntchangesfunctions import logic
from rntchangesfunctions import gettime
from rntchangesfunctions import get_runtime_exclude_list
from rntchangesfunctions import load_config
from rntchangesfunctions import openrc
from rntchangesfunctions import epoch_to_date

from pyfunctions import green
from pyfunctions import cprint
from pyfunctions import escf_py
from pyfunctions import parse_datetime

from ulink import ulink


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


# parsing python
#
# def read_file_lines(path):
#     p = Path(path)
#     return [line.rstrip() for line in p.open()] if p.is_file() and p.stat().st_size > 0 else []

# def extract_quoted(line):
#     m = re.search(r'"((?:[^"\\]|\\.)*)"', line)
#     return m.group(1) if m else ""

# UTC join
def timestamp_from_line(line):
    parts = line.split()
    return " ".join(parts[:2])

def line_included(line, patterns):
    return not any(p in line for p in patterns)
                                                                                                                                            #
                                                                                                                    # end parsing #


# Parallel SORTCOMPLETE search and  ctime hashing
#
def calculate_checksum(file_path):
    try:
        hash_func = hashlib.md5()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception:
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
    fmt="%Y-%m-%d %H:%M:%S"
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

    mtime = epoch_to_date(mod_time, fmt)
    atime = epoch_to_date(access_time, fmt)
    ctime = epoch_to_date(change_time, fmt)

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


def hsearch(OLDSORT, MODULENAME, argone):
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


    cstart, cend = 0
    CSZE = 1024 * 1024  # >= 1MB in bytes to cache

    diffrlt = False
    samerlt = False
    nodiff = False
    syschg = False
    flsrh = "false"
    validrlt = ""
    fmt="%Y-%m-%d %H:%M:%S"

    chxzm="/rntfiles.xzm"
    filename = os.path.basename(chxzm)  
    LCLMODULENAME = os.path.splitext(filename)[0]
    MODULENAME= os.path.splitext(chxzm)[0]
    USRDIR =  f'/home/{USR}/Downloads'    

    flth="/usr/local/save-changesnew/flth.csv"
    log_file="/tmp/file_creation_log.txt"
    CACHE_F="/tmp/ctimecache"
    slog="/tmp/scr"
    cerr="/tmp/cerr"
    toml="/usr/local/save-changesnew/config.toml"
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
    archivesrh = config['search']['archivesrh'] 
    cmode = config['search']['cmode'] 
    turbo = config['search']['mMODE']
    xRC = config ['search']['xRC']
   

    start = gettime(ANALYTICSECT, start)
    # start inotifywait?
    if xRC:
        tout = openrc(log_file, CACHE_F, checksum, tout) 

    # init
    nc=intst(dbtarget, logSIZE, CSZE, compLVL)

    TEMPDIR = tempfile.mkdtemp()
    #tfile=TEMPDIR + '/' + 'tmpd' formerly copy of rout with 3 fields

    # user arguments mode time/file
    if argone != "noarguser" and argone != "":
        try:
            argone = int(argone)
            p = 60
            tmn = argone / p
            if argone % p == 0:
                tmn = argone // p
            cprint.cyan(f"Searching for files {argone} seconds old or newer")

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

            cprint.cyan(f"Searching for files newer than {filename}")

            flsrh = "true"
            ct = int(time.time())
            fmt = int(os.stat(filename).st_mtime)
            ag = ct - fmt
            mmin = f'-newer {filename}'
            cmin = f'-cmin -{ag}'

    else:
        argone = 5
        tmn = argone
        cprint.cyan('Searching for files 5 minutes old or newer')

    if tmn:
        logf=RECENT
        mmin = f'-mmin -{tmn}'
        cmin = f'-cmin -{tmn}'



    if not tout: # is there xRC? if not both mtime and ctime (toutnul)

        directories = ["/bin", "/etc", "/home", "/lib", "/lib64", "/opt", "/root", "/sbin", "/tmp", "/usr", "/var"]

        find_base_command = ['find'] + directories + ['-not', '-type', 'd', '-printf', '%T@ %A@ %C@ %i %s %u %g %m %p\0']

        find_command_mmin = find_base_command + [mmin]
        find_command_cmin = find_base_command + [cmin]

        mmin_lines = subprocess.run(find_command_mmin, capture_output=True, text=True, check=True)
        cmin_lines = subprocess.run(find_command_cmin, capture_output=True, text=True, check=True)

        end, cstart = gettime(ANALYTICSECT, checksum, start, cstart)
        toutnul = cmin_lines.stdout.splitlines()

        tout, COMPLETE_2 = process_find_lines(toutnul, CACHE_F, CSZE) # ctime > mtime files

    # bypass ctime loop
    else:

        find_command_mmin = find_base_command + [mmin]

        end, cstart = gettime(ANALYTICSECT, checksum, "init", start, cstart)
        end, cstart = gettime(ANALYTICSECT, checksum, "init", start, cstart)

    RECENTNUL = mmin_lines.stdout.splitlines()

    SORTCOMPLETE, COMPLETE_1 = process_find_lines(RECENTNUL, CACHE_F, CSZE) # mtime files main
    cend = gettime(ANALYTICSECT, cend)

    COMPLETE = COMPLETE_1 + COMPLETE_2 # nsf system cache items

    if FEEDBACK: # scrolling terminal look
        for file_info in RECENTNUL:
            print(file_info)


    parsed_lines = []

    # merge all times from ctime >= to SORTCOMPLETE into same
    for l in SORTCOMPLETE:
        ts = parse_datetime(timestamp_from_line(l), fmt)
        if ts:
            parsed_lines.append((ts, l))

    parsed_lines.sort(key=lambda x: x[0])

    SRTTIME = timestamp_from_line(parsed_lines[0][1]) if parsed_lines else datetime.now().strftime(fmt)
    parsed_PRD = parse_datetime(SRTTIME, fmt)

    for l in tout:
        ts = parse_datetime(timestamp_from_line(l), fmt)
        if ts and ts >= parsed_PRD:
            parsed_lines.append((ts, l))

    # Deduplicate
    seen = set()
    TMPOUTPUT = []
    for ts, line in parsed_lines:
        if line not in seen:
            seen.add(line)
            TMPOUTPUT.append((ts, line))

    # inclusions from this script
    exclude_patterns = get_runtime_exclude_list(USR, logpst, statpst, dbtarget)
    filtered_lines = [line for ts, line in TMPOUTPUT if line_included(line, exclude_patterns)]


    if updatehlinks:
        green('Updating hardlinks')
        SORTCOMPLETE = ulink(SORTCOMPLETE, LCLMODULENAME, supbrw)

    # <=
    if flsrh != "true":
        start_dt = parse_datetime(SRTTIME, fmt)
        range_sec = 300 if argone == 'noarguser' else int(argone)
        end_dt = start_dt + timedelta(seconds=range_sec)
        lines = [l for ts, l in TMPOUTPUT if parse_datetime(timestamp_from_line(l), fmt) <= end_dt]
    else:
        lines = filtered_lines

    # preprocess
    final_output = []
    for line in filtered_lines:
        parts = line.strip().split(maxsplit=2)
        if len(parts) < 3:
            continue
        ts_str = f"{parts[0]} {parts[1]}"

        filepath = parts[2]
        escaped_path = escf_py(filepath)
        final_output.append(f"{ts_str} {escaped_path}")


    tmp_lines = [l for l in final_output if l.split(" ", 2)[2].startswith("/tmp")]
    non_tmp_lines = [l for l in final_output if not l.split(" ", 2)[2].startswith("/tmp")]

     # 'recentchanges search'
    if method != "rnt": 
        SORTCOMPLETE = [l for l in lines if not l.split(maxsplit=2)[2].startswith("/tmp")]
        TMPOPT = non_tmp_lines
    else:  # 'recentchanges'
        SORTCOMPLETE = lines
        TMPOPT = tmp_lines


    RECENT = TMPOPT[:]


    # invert flag from filteredsearch.sh "inv"
    if argf == "filtered" or flsrh == "true":
        logf = TMPOPT # filter the search
        if argf == "filtered" and flsrh == "true": # Inv
            logf = RECENT # dont filter

    TMPOPT = filter_lines_from_list(TMPOPT, USR)  # Apply filter used for results, copying. RECENT is stored in db.




    records = RECENT.strip().splitlines()

    with open(TEMPDIR + "/list_recentchanges_filtered.txt", "w") as f_filtered:
        for record in records:
            fields = record.strip().split(" ", 9) 
            if len(fields) > 9:
                path_rest = fields[9]
                
                # $RECENT
                f_filtered.write(path_rest + "\n")
    
    
    # Copy here? save escaping...     
    #
    #
   # Copy logic re changes .xzm
    try:
        copyres = subprocess.run(
            ['/usr/local/save-changesnew/recentchanges', THETIME, argone, USR, TEMPDIR, archivesrh, cmode], # 
            capture_output=True,
            text=True
        )

        if copyres.returncode == 7:
            validrlt = "nofiles"
        elif copyres.returncode ==3:
            print(f'RECENT is missing exiting from recentchanges.')
        elif copyres.returncode != 0:
            print(f'/rntfiles.xzm failed to unable to make xzm. {copyres.returncode}')
            #print("STDERR:", result.stderr)
        else:
            validrlt = "True"

    except Exception as e:
        print(f"Error running script: {e}")

    # 'recentchanges'             /tmp                   logic in /usr/local/save-changesnew/recentchanges  --> moves
    # 'recentchanges search'  USRDIR              logic here  -->  moves
    #
    #
    #
    #
    #

    #Merge/Move
    if SORTCOMPLETE:
        OLDSORT = []

        if flsrh == "true":
            flnm = f'xNewerThan_{parseflnm}{argone}'
            flnmdff = f'xDiffFromLast_{parseflnm}{argone}'
        elif argf == "filtered":
            flnm = f'xFltchanges_{argone}'
            flnmdff = f'xFltDiffFromLastSearch_{argone}'
        else:
            flnm = f'xSystemchanges{argone}'
            flnmdff = f'xSystemDiffFromLastSearch{argone}'

        if method == "rnt":
            DIRSRC="/tmp"
        else:
            DIRSRC=USRDIR

            filepath = os.path.join(DIRSRC, f'{MODULENAME}{flnm}')

        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                OLDSORT = f.readlines()

        if not OLDSORT and flsrh != "true" and argf != "filtered" and method != "rnt":
            fallback_path = f'/tmp/{MODULENAME}{flnm}'
            if os.path.exists(fallback_path):
                with open(fallback_path, 'r') as f:
                    OLDSORT = f.readlines()

            if not OLDSORT:
                    hsearch(MODULENAME, argone) # look through `recentchanges` /tmp/MODULENAME_MDY*

        uid = pwd.getpwnam(USR).pw_uid

        if method != "rnt":
            # Reset
            clear_logs(USRDIR, MODULENAME)

            # send /tmp results to user
            if TMPOUTPUT:

                b_argone = argone.replace('.txt', '') if argone.endswith('.txt') else argone
                target_filename = f"{MODULENAME}xSystemTmpfiles{flnm}{b_argone}"
                target_path = os.path.join(USRDIR, target_filename)


                with open(target_path, 'w') as dst:
                    dst.write('\n'.join(TMPOUTPUT) + '\n')  # join lines with newlines
                    
                os.chown(target_path, uid, -1)

        # Is diff?
        if OLDSORT:
            nodiff = True
            toutnul = [line.strip() for line in OLDSORT]
            sortcomplete_stripped = [line.strip() for line in logf]

            diffnm=f'{DIRSRC}{MODULENAME}{flnmdff}'
            difff_file = [line for line in toutnul if line not in sortcomplete_stripped]

            if difff_file:
                diffrlt = True
                with open(diffnm, 'w') as f:
                    for line in difff_file:
                        f.write(line + '\
                                n')
                os.chown(diffnm, uid, -1)
            else:
                samerlt = True

            # Send search result SORTCOMPLETE to user
            with open(filepath, 'w') as f:
                f.write("\n".join(logf) + "\n")

            os.chown(filepath, uid, -1)
       
            # postprocess before db/ha and then send to processha
            isdiff(RECENT, ABSENT, rout, diffnm, difff_file, parsed_PRD, fmt)

    # Backend
    pstsrg.main(SORTCOMPLETE, COMPLETE, dbtarget, rout, checksum, cdiag, email, turbo, ANALYTICSECT, ps, nc, USR)


    csum=processha(rout, ABSENT, diffnm, cerr, TMPOPT, flsrh, LCLMODULENAME, argf, parsed_PRD, USR, supbrw, supress)
    # filter hits
    update_filter_csv(TMPOPT, USR, flth) 

    # terminal opt
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

    if ANALYTICSECT:
        el = end - start  
        print(f'Search took {el:.3f} seconds')
        if checksum:
            el = cend - cstart
            print(f'Checksum took {el:.3f} seconds')

    #cleanup
    
    try:
        shutil.rmtree(TEMPDIR)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Error removing temporary directory {TEMPDIR}: {e}")

    logic(syschg, samerlt, nodiff, diffrlt, validrlt, copyres, MODULENAME, THETIME, argone, argf, filename, flsrh, imsg)
    display(dspEDITOR, USRDIR, MODULENAME, flnm)

