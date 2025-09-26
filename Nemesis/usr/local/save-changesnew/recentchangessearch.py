#!/usr/bin/env python3                  
#   Porteus                                                                           09/24/2025 
#   recentchanges. Developer buddy      `recentchanges`/ `recentchanges search`       
#   Provide ease of pattern finding ie what files to block we can do this a number of ways
#   1) if a file was there (many as in more than a few) and another search lists them as deleted its either a sys file or not but unwanted nontheless
#   2) Is a system file inherent to the specifc platform
#   3) intangibles ie trashed items that may pop up infrequently and are not known about
#
#   This script is called by two methods. recentchanges and recentchanges search. The former is discussed below
#
#   `recentchanges` make xzm
#           Searches are saved in /tmp
#           1. Search results are unfiltered and copied files for the .xzm are from a filter.
#
#           The purpose of this script is to save files ideally less than 5 minutes old. So when compiling or you dont know where some files are
#   or what changed on your system. So if you compiled something you call this script to build a module of it for distribution. If not using for developing 
#   call it a file change snapshot
#   We use the find command to list all files 5 minutes or newer. Filter it and then get to copying the files in a temporary staging directory.
#   Then take those files and make an .xzm. It will be placed in   /tmp  along with a transfer log to staging directory and file manifest of the xzm
#
#   `recentchanges search`
#           Searches are saved in /home/{user}/Downloads
#
#           This has the same names as `recentchanges` but also includes /tmp files and or a filesearch.
#           1. old searches can be grabbed from /Downloads, /tmp or /tmp/{MODULENAME}_MDY. for convenience if there is no differences it displays the old search for specified search criteria
#           2. The search is unfiltered and a filesearch is filtered.
#           2. rnt search inverses the results. For a standard search it will filter the results. For a file search it removes the filter.
#
#  Also borred script features from various scripts on porteus forums

import os
import sys
import time
import processha
import pstsrg
import pwd
import subprocess
import tempfile
from datetime import timedelta

from filterhits import update_filter_csv
from fsearch import process_find_lines
from processha import isdiff
from rntchangesfunctions import changeperm
from rntchangesfunctions import clear_logs
from rntchangesfunctions import copyfiles
from rntchangesfunctions import display
from rntchangesfunctions import filter_lines_from_list
from rntchangesfunctions import filter_output
from rntchangesfunctions import gettime
from rntchangesfunctions import get_runtime_exclude_list
from rntchangesfunctions import hsearch
from rntchangesfunctions import logic
from rntchangesfunctions import load_config
from rntchangesfunctions import openrc
from pyfunctions import cprint
from pyfunctions import escf_py
from ulink import ulink

#import shutil
#from functools import partial
#from pathlib import Path
# from pyfunctions import unescf_py
# from pyfunctions import parse_datetime

# Initialize
def intst(dbtarget, logSIZE, CSZE, compLVL):
    if os.path.isfile(dbtarget):
        try:
            file_size = os.stat(dbtarget).st_size       
            # return true to disable comp on large files
            return file_size // CSZE >= compLVL  

        except Exception as e:
            print(f"Error checking or modifying log file: {e}")
            return False
    return False

RECENTNUL = b""  # filepaths `recentchanges`

def main():

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
    dbtarget = config['paths']['pydbpst']
    archivesrh = config['search']['archivesrh'] 
    cmode = config['search']['cmode'] 
    turbo = config['search']['mMODE']
    xRC = config ['search']['xRC']

    argone=sys.argv[1] # range
    argtwo=sys.argv[2] # SRC tag?
    USR=sys.argv[3]         # getpass.getuser()
    uid = pwd.getpwnam(USR).pw_uid   #chown
    pwrd=sys.argv[4]
    argf=sys.argv[5] # filtered?
    method=""
    if len(sys.argv) > 6:
        method=sys.argv[6]
    imsg=None
    if len(sys.argv) > 7:
        imsg=sys.argv[7] # custom closing terminal message

    if sys.argv[5] is None:
        print('please call from recentchanges')
        sys.exit(0)

    if method != "rnt" and argone.lower() != 'search':
        print('exiting not a search')
        sys.exit(0)     

    TMPOUTPUT = [] # holding   
    # Searches
    RECENT = [] # main results
    tout = [] # ctime results
    SORTCOMPLETE = [] # combined
    TMPOPT = [] # combined filtered
    # NSF
    COMPLETE_1 = [] 
    COMPLETE_2 = []
    COMPLETE = [] # combined
    # Diff file
    difff_file = [] 
    ABSENT = [] # actions
    rout = [] # actions from ha

    start = 0 
    end = 0
    cstart = 0
    cend = 0
    CSZE = 1024 * 1024  # >= 1MB in bytes to cache

    diffrlt = False
    samerlt = False
    nodiff = False
    syschg = False
    flsrh = "false"
    validrlt = ""
    copyres = ""
    parseflnm = ""
    fmt="%Y-%m-%d %H:%M:%S"

    chxzm="/rntfiles.xzm" # custom modulename retain leading / and trailing .xzm
    USRDIR =  f'/home/{USR}/Downloads'    
    flth="/usr/local/save-changesnew/flth.csv" # filter hits
    log_file="/tmp/file_creation_log.txt" # ctime from watchdog
    CACHE_F="/tmp/ctimecache" # watchdog cache
    slog="/tmp/scr" # feedback
    cerr="/tmp/cerr" # priority

    filename = os.path.basename(chxzm) # parse 
    MODULENAME = os.path.splitext(filename)[0]  # file label

    F= [ 
        "find",
        "/bin", "/etc", "/home", "/lib", "/lib64", "/opt", "/root", "/sbin", "/tmp", "/usr",  "/var"
    ]
    
    TAIL = ["-not", "-type", "d", "-printf", "%T@ %A@ %C@ %i %s %u %g %m %p\\0"]

    #F= "find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var"
    #TAIL="-not -type d -printf '%T@ %A@ %C@ %i %s %u %g %m %p\\0'"


    start = gettime(ANALYTICSECT, start)

    # initialize
    # start inotifywait?
    if xRC:
        openrc(log_file, CACHE_F, checksum, tout) 
    nc=intst(dbtarget, logSIZE, CSZE, compLVL)
    with tempfile.TemporaryDirectory(dir='/tmp') as TEMPDIR:

        if argone != "search":
            THETIME=argone
        else:
            THETIME=argtwo

        # search criteria
        if THETIME != "noarguser":
            try:
                argone = int(THETIME)
                p = 60
                tmn = argone / p
                if argone % p == 0:
                    tmn = argone // p
                cprint.cyan(f"Searching for files {argone} seconds old or newer")

            except ValueError: # its a file search

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
            # mmin = f'-mmin -{tmn}'
            # cmin = f'-cmin -{tmn}'
            cmin = ["-cmin", f"-{tmn}"]
            mmin = ["-mmin", f"-{tmn}"]

        # find_command_cmin =f"{F} {cmin} {TAIL}"
        # find_command_mmin =f"{F} {mmin} {TAIL}"
        find_command_cmin = F + cmin + TAIL
        find_command_mmin = F + mmin + TAIL


        def find_files(find_command, file_type, RECENT, COMPLETE, init, checksum, ANALYTICSECT, end, cstart):
            global RECENTNUL
            table = "logs"
            proc = subprocess.Popen(find_command, stdout=subprocess.PIPE)
            output, _ = proc.communicate()
            # output = proc.stdout.read()
            # proc.stdout.close()
            # proc.wait()

            file_entries = [entry.decode() for entry in output.split(b'\0') if entry]

            end, cstart = gettime(ANALYTICSECT, checksum, init, start, cstart)

            if file_type == "mtime":
                for entry in file_entries:
                    fields = entry.split()
                    if len(fields) >= 9: 
                        file_path = fields[8]
                        print(file_path)
                        RECENTNUL += (file_path.encode() + b'\0')

                RECENT, COMPLETE = process_find_lines(file_entries, checksum, "main", table, CACHE_F, CSZE)
            elif file_type == "ctime":
                RECENT, COMPLETE = process_find_lines(file_entries, checksum, "ctime", table, CACHE_F, CSZE)
            else:
                raise ValueError(f"Unknown file type: {file_type}")

            return RECENT, COMPLETE, end, cstart


        if not tout: 
            tout, COMPLETE_2, end, cstart = find_files(find_command_cmin, "ctime", tout, COMPLETE_2, "init", checksum, ANALYTICSECT, end, cstart)
            RECENT, COMPLETE_1, end, cstart = find_files(find_command_mmin, "mtime", RECENT, COMPLETE_1, "false", checksum, ANALYTICSECT, end, cstart)
        else:
            RECENT, COMPLETE_1, end, cstart = find_files(find_command_mmin, "mtime", RECENT, COMPLETE_1, "init", checksum, ANALYTICSECT, end, cstart) # bypass ctime loop if xRC 
        cend = gettime(ANALYTICSECT, cend)
        SORTCOMPLETE = RECENT

        if not SORTCOMPLETE:
            cprint.cyan("No files found or invalid search criteria ")
            return
        COMPLETE = COMPLETE_1 + COMPLETE_2 # nsf append to rout
        if FEEDBACK: # scrolling terminal look
            for file_info in RECENTNUL:
                print(file_info)


        SORTCOMPLETE = RECENT
        SORTCOMPLETE.sort(key=lambda x: x[0])
        SRTTIME = SORTCOMPLETE[0][0]

        merged = SORTCOMPLETE[:]
        for entry in tout:
            tout_dt = entry[0]
            if tout_dt >= SRTTIME:
                merged.append(entry)
    
        merged.sort(key=lambda x: x[0])
        seen = {}

        for entry in merged:
            
            timestamp_truncated = entry[0].replace(microsecond=0)
            filepath = entry[1]
            cam_flag = entry[10]  # new entry's cam flag

            key = (timestamp_truncated, filepath)

            if key not in seen:
                seen[key] = entry
            else:
                existing_entry = seen[key]
                existing_cam = existing_entry[10]

                # Prefer non change as modified time
                if existing_cam == "y" and cam_flag == "":
                    seen[key] = entry


        deduped = list(seen.values())

        
        exclude_patterns = get_runtime_exclude_list(USR, logpst, statpst, dbtarget) # inclusions from this script

        # sort -u 
        def filepath_included(filepath, exclude_patterns):
            for pattern in exclude_patterns:
                if pattern in filepath:
                    return False
            return True

        SORTCOMPLETE = [
            entry for entry in deduped
            if filepath_included(entry[1], exclude_patterns)
        ]


        # hardlinks?
        # if updatehlinks:
        #     cprint.green('Updating hardlinks')
        #     SORTCOMPLETE = ulink(SORTCOMPLETE, MODULENAME, supbrw)


        filtered_lines = []
        for entry in SORTCOMPLETE:
            ts_str = entry[0]
            filepath = entry[1]
            escaped_path = escf_py(filepath)
            filtered_lines.append((ts_str, escaped_path))


        if flsrh != "true":
            start_dt = SRTTIME
            range_sec = 300 if THETIME == 'noarguser' else int(THETIME)
            end_dt = start_dt + timedelta(seconds=range_sec)

            lines = [entry for entry in filtered_lines if entry[0] <= end_dt]
        else:
            lines = filtered_lines

        tmp_lines = [entry for entry in lines if entry[1].startswith("/tmp")]
        non_tmp_lines = [entry for entry in lines if not entry[1].startswith("/tmp")]
        TMPOPT = non_tmp_lines
        TMPOUTPUT = tmp_lines
        RECENT = TMPOPT[:]

        TMPOPT = filter_lines_from_list(TMPOPT, USR)  # Apply filter used for results, copying. RECENT is stored in db.
    


        if tmn:
            logf = RECENT # all files
        elif method == "rnt":
            logf = TMPOPT # filtered
        if argf == "filtered" or flsrh == "true":
            logf = TMPOPT # filtered
            if argf == "filtered" and flsrh == "true":
                logf = RECENT # dont filter inverse

        
        # Copy files
        validrlt = copyfiles(RECENT, TMPOPT, method, argone, argtwo, USR, TEMPDIR, archivesrh, cmode, fmt)
        
   
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
                DIRSRC="/tmp"  # 'recentchanges'
            else:
                DIRSRC=USRDIR # 'search'

            # is old search?
            filepath = os.path.join(DIRSRC, f'{MODULENAME}{flnm}')
            
            if os.path.isfile(filepath):
                with open(filepath, 'r') as f:
                    OLDSORT = f.readlines()

            # try /tmp for previous search
            if not OLDSORT and flsrh != "true" and argf != "filtered" and method != "rnt":
                fallback_path = f'/tmp/{MODULENAME}{flnm}'
                if os.path.isfile(fallback_path):
                    with open(fallback_path, 'r') as f:
                        OLDSORT = f.readlines()

                # try `recentchanges` searches
                if not OLDSORT:
                    hsearch(OLDSORT, MODULENAME, argone) # look through `recentchanges` /tmp/MODULENAME_MDY*



            # move/output /tmp file results 
            if method != "rnt":
                # Reset
                clear_logs(USRDIR, MODULENAME)
                # send /tmp results to user
                if TMPOUTPUT:
                    b_argone = str(argone).replace('.txt', '') if str(argone).endswith('.txt') else str(argone)
                    target_filename = f"{MODULENAME}xSystemTmpfiles{parseflnm}{b_argone}"
                    target_path = os.path.join(USRDIR, target_filename)
                    with open(target_path, 'w') as dst:
                        for entry in TMPOUTPUT:
                            tss = entry[0].strftime(fmt)
                            fp = entry[1]
                            dst.write(f'{tss} {fp}\n')
                    changeperm(target_path, uid)
    
            diffnm = os.path.join(DIRSRC, MODULENAME +  flnmdff)

            # Difference file
            if OLDSORT:
                nodiff = True

                clean_oldsort = [line.strip() for line in OLDSORT]

                clean_logf_set = set(f'{entry[0].strftime(fmt)} {entry[1]}' for entry in logf)

                difff_file = [line for line in clean_oldsort if line not in clean_logf_set]

                if difff_file:
                    diffrlt = True

                    with open(diffnm, 'a') as file2:
                        for entry in difff_file:
                            print(entry, file=file2)
                        file2.write("\n")    

                    # preprocess before db/ha. The differences before ha and then sent to processha after ha
                    isdiff(logf, ABSENT, rout, diffnm, difff_file, flsrh, SRTTIME, uid, fmt) 
                    
                else:
                    samerlt = True


            #Send search result SORTCOMPLETE to user
            with open(filepath, 'w') as f:
                    for entry in logf:
                        tss = entry[0].strftime(fmt)
                        fp = entry[1]
                        f.write(f'{tss} {fp}\n')
            changeperm(filepath, uid)


            # Backend
            rlt = pstsrg.main(SORTCOMPLETE, COMPLETE, dbtarget, rout, checksum, cdiag, email, turbo, ANALYTICSECT, ps, nc, USR)
            if rlt != 0:
                if rlt == 2 or rlt == 3:
                    print("Problem with GPG refer to instructions on setting up pinentry ect. Database preserved.")
                elif rlt == 4:
                    print("Problem with database in psysrg.py")
                # elif rlt == 7:
                #     print("mem failed in pstsrg.py")
                # elif rlt == 87:
                #     print("failed to parse from mMODE=\"mem\"")
                else:
                    print(f'Pstsrg.py failed. exitcode ${rlt}')


            # Diff output
            csum=processha.processha(rout, ABSENT, diffnm, cerr, flsrh, MODULENAME, argf, SRTTIME, USR, supbrw, supress, fmt)
            # Filter hits
            update_filter_csv(RECENT, USR, flth) 

            # Terminal output
            if not csum and os.path.exists(slog) and supress:
                with open(slog, 'r') as src, open(diffnm, 'a') as dst:
                    dst.write(f"\ncdiag\n")
                    dst.write(src.read())
            elif not csum and not supress and os.path.exists(slog):
                filter_output(slog, MODULENAME, 'Checksum', 'no', 'blue', 'yellow', 'scr')
                with open(slog, 'r') as src, open(diffnm, 'a') as dst:
                    dst.write(f"\ncdiag\n")
                    dst.write(src.read())
            elif csum:
                with open(cerr, 'r') as src, open(diffnm, 'a') as dst:
                    dst.write(f"\ncdiag alert\n")
                    dst.write(src.read())
                try:
                    os.remove(cerr)
                except Exception as e:
                    print(f'Problem removing {cerr}')
                except FileNotFoundError:
                    pass

            if ANALYTICSECT:
                el = end - start  
                print(f'Search took {el:.3f} seconds')
                if checksum:
                    el = cend - cstart
                    print(f'Checksum took {el:.3f} seconds')

            try:
                logic(syschg, samerlt, nodiff, diffrlt, validrlt, copyres, MODULENAME, THETIME, argone, argf, filename, flsrh, imsg, method)
                display(dspEDITOR, USRDIR, MODULENAME, flnm)
            except Exception as e:
                print(f"Error in logic or display: {e}")

            #Cleanup
            try:
                if os.path.isfile(slog):
                    os.remove(slog)
            except FileNotFoundError:
                 pass
            except Exception as e:
                 print(f"Error removing scr feedback {slog}: {e}")               



if __name__ == "__main__":
    main()


# Notes/drafted/cut
    #Cleanup
    # try:
    #     shutil.rmtree(TEMPDIR)
    # except FileNotFoundError:
    #     pass
    # except Exception as e:
    #     print(f"Error removing temporary directory {TEMPDIR}: {e}")

                #if file_size // CSZE > logSIZE: 
            #    print('db exceeding size limit')
#                 if logPRF == "del":
#                     open(logpst, 'w').close()  # Clear the file
#                 elif logPRF == "stop":
#                     print("persist log saving stopped on size limit")
#                 STATPST = "false"            
#                 if logPRF == "rfh":
#                     os.remove(logpst)
#                     STATPST = "true"

#             elif file_size == 0:
#                 print(f"{logpst} is 0 bytes. To resume persistent logging, delete the file")
#                 STATPST = "false"
#
    #TEMPDIR = tempfile.mkdtemp()
    #tfile=TEMPDIR + '/' + 'tmpd' formerly copy of rout with 3 fields