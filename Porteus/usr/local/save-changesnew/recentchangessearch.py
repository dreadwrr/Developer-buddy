#!/usr/bin/env python3                  
#   Porteus                                                                           09/27/2025 
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
import csv
import os
import sys
import processha
import pstsrg
import pwd
import signal
import subprocess
import tempfile
import time
from datetime import timedelta
from filterhits import update_filter_csv
from fsearch import process_find_lines
from io import StringIO
from processha import isdiff
from pstsrg import decrm
from pstsrg import dict_string
from pstsrg import encrm
from rntchangesfunctions import changeperm
from rntchangesfunctions import clear_logs
from rntchangesfunctions import copyfiles
from rntchangesfunctions import display
from rntchangesfunctions import filter_lines_from_list
from rntchangesfunctions import filter_output
from rntchangesfunctions import get_runtime_exclude_list
from rntchangesfunctions import hsearch
from rntchangesfunctions import iskey
from rntchangesfunctions import logic
from rntchangesfunctions import load_config
from rntchangesfunctions import removefile
from rntchangesfunctions import postop
from pyfunctions import cprint
from pyfunctions import escf_py
from ulink import ulink

def sighandle(signum, frame):
    global stopf
    if signum == 2:
        stopf = True
        sys.exit()
        
signal.signal(signal.SIGINT, sighandle)
signal.signal(signal.SIGTERM, sighandle)

# Initialize
def intst(dbtarget, CSZE, compLVL):
    if os.path.isfile(dbtarget):
        try:
            file_size = os.stat(dbtarget).st_size       

            return file_size // CSZE >= compLVL  # no compression

        except Exception as e:
            print(f"Error checking or modifying log file: {e}")
            return False
    return False


def convertn(quot, divis, decm):
    tmn = round(quot / divis, decm)
    if quot % divis == 0:
        tmn = quot // divis
    return tmn
#Globals
stopf=False
RECENTNUL = b""  # filepaths `recentchanges`

def main():

    toml="/home/guest/.config/save-changesnew/config.toml"
    config = load_config(toml)

    FEEDBACK = config['analytics']['FEEDBACK']
    ANALYTICSECT = config['analytics']['ANALYTICSECT']
    compLVL = config['logs']['compLVL']
    dspEDITOR = config['display']['dspEDITOR']
    email = config['backend']['email']
    checksum = config['diagnostics']['checkSUM']
    cdiag = config['diagnostics']['cdiag']
    supbrw = config['diagnostics']['supbrw']
    supress = config['diagnostics']['supress']
    POSTOP = config['diagnostics']['POSTOP']
    ps = config['diagnostics']['proteusSHIELD'] # proteus shield
    updatehlinks = config['diagnostics']['updatehlinks']
    flth=config['paths']['flth']  # filter hits
    logpst  = config['paths']['logpst'] # for inclusions
    statpst = config['paths']['statpst']
    dbtarget = config['paths']['pydbpst']
    CACHE_F=config['paths']['CACHE_F']
    archivesrh = config['search']['archivesrh']
    autooutput = config['search'] ['autooutput']
    cmode = config['search']['cmode'] 

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

    cfr = [] # cache dict

    start = 0 
    end = 0
    cstart = 0
    cend = 0
    CSZE = 1024 * 1024  # >= 1MB in bytes to cache

    tmn = None
    filename = None
    diffrlt = False
    nodiff = False
    syschg = False
    flsrh = False
    validrlt = None
    parseflnm = ""
    fmt="%Y-%m-%d %H:%M:%S"

    MODULENAME="rntfiles" # file label

    USRDIR =  f'/home/{USR}/Downloads'    
    
    F= [ 
        "find",
        "/bin", "/etc", "/home", "/lib", "/lib64", "/opt", "/root", "/sbin", "/tmp", "/usr",  "/var"
    ]
    
    TAIL = ["-not", "-type", "d", "-printf", "%T@ %A@ %C@ %i %s %u %g %m %p\\0"]

    TEMPD = tempfile.gettempdir()
    slog=TEMPD + "/scr" # feedback
    cerr=TEMPD + "/cerr" # priority

    with tempfile.TemporaryDirectory(dir=TEMPD) as mainl:   

        iskey(email, mainl) 

        if os.path.isfile(CACHE_F):
            csv_path = decrm(CACHE_F)

            if csv_path:
                reader = csv.DictReader(StringIO(csv_path), delimiter='|')
                cfr = list(reader)


        start = time.time()

        # initialize
        nc=intst(dbtarget, CSZE, compLVL)


        if argone != "search":
            THETIME=argone
        else:
            THETIME=argtwo

        # search criteria
        if THETIME != "noarguser":
            p = 60
            try:
                argone = int(THETIME)
                tmn = convertn(argone, p, 2)
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
                flsrh = True
                ct = int(time.time())
                frmt = int(os.stat(filename).st_mtime)
                ag = ct - frmt
                ag = convertn(ag, p, 2)
                mmin = ["-newer", f"{filename}"]
                cmin = ["-cmin", f"-{ag}"]

        else:
            argone = 5
            tmn = argone
            cprint.cyan('Searching for files 5 minutes old or newer')

        if tmn is not None:
            cmin = ["-cmin", f"-{tmn}"]
            mmin = ["-mmin", f"-{tmn}"]

        find_command_cmin = F + cmin + TAIL
        find_command_mmin = F + mmin + TAIL


        def find_files(find_command, file_type, RECENT, COMPLETE, init, checksum, cfr, ANALYTICSECT, end, cstart):
            global RECENTNUL
            table = "logs"
            proc = subprocess.Popen(find_command, stdout=subprocess.PIPE) # stderr=subprocess.DEVNULL 
            output, _ = proc.communicate()

            file_entries = [entry.decode() for entry in output.split(b'\0') if entry]
            if file_type == "mtime":
                end = time.time()
                if FEEDBACK: # scrolling terminal look       alternative output
                    for entry in file_entries:
                        fields = entry.split(maxsplit=8)
                        if len(fields) == 9:
                            print(fields[8])

            # using escf_py and unesc_py for bash support otherwise can use below
            # filename.encode('unicode_escape').decode('ascii')
            # codecs.decode(escaped, 'unicode_escape')
            escaped = []

            for entry in file_entries:
                fields = entry.split(maxsplit=8)
                if len(fields) == 9:
                    file_path = escf_py(fields[8])
                    fields[8] = file_path
                    escaped_entry = " ".join(fields)
                    escaped.append(escaped_entry)
                    RECENTNUL += (file_path.encode() + b'\0') # copy file list `recentchanges` null byte

            if init and checksum:
                cstart = time.time()
                cprint.cyan('Running checksum.')
            if file_type == "mtime":
                RECENT, COMPLETE = process_find_lines(escaped, checksum, "main", table, cfr, CSZE)
            elif file_type == "ctime":
                RECENT, COMPLETE = process_find_lines(escaped, checksum, "ctime", table, cfr, CSZE)
            else:
                raise ValueError(f"Unknown file type: {file_type}")

            return RECENT, COMPLETE, end, cstart


        if not tout: 
            tout, COMPLETE_2, end, cstart = find_files(find_command_cmin, "ctime", tout, COMPLETE_2, True, checksum, cfr, ANALYTICSECT, end, cstart)
            RECENT, COMPLETE_1, end, cstart = find_files(find_command_mmin, "mtime", RECENT, COMPLETE_1, False, checksum, cfr, ANALYTICSECT, end, cstart)
        else:
            RECENT, COMPLETE_1, end, cstart = find_files(find_command_mmin, "mtime", RECENT, COMPLETE_1, True, checksum, cfr, ANALYTICSECT, end, cstart) # bypass ctime loop if xRC 
        if ANALYTICSECT:
            cend = time.time()


        SORTCOMPLETE = RECENT

        if not SORTCOMPLETE:
            cprint.cyan("No files found or invalid search criteria ")
            return
        
        COMPLETE = COMPLETE_1 + COMPLETE_2 # nsf append to rout
        
        SORTCOMPLETE = RECENT
        SORTCOMPLETE.sort(key=lambda x: x[0])
        SRTTIME = SORTCOMPLETE[0][0]

        # get everything from the start time
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
            cam_flag = entry[10]  

            key = (timestamp_truncated, filepath)

            if key not in seen:
                seen[key] = entry
            else:
                existing_entry = seen[key]
                existing_cam = existing_entry[10]

                # Prefer non change as modified time
                if existing_cam == "y" and cam_flag is None:
                    seen[key] = entry


        deduped = list(seen.values())

        # inclusions from this script. sort -u 
        exclude_patterns = get_runtime_exclude_list(USR, logpst, statpst, dbtarget, CACHE_F) 

        def filepath_included(filepath, exclude_patterns):
            for pattern in exclude_patterns:
                if pattern in filepath:
                    return False
            return True

        SORTCOMPLETE = [
            entry for entry in deduped
            if filepath_included(entry[1], exclude_patterns)
        ]


        #hardlinks?
        if updatehlinks:
            cprint.green('Updating hardlinks')
            SORTCOMPLETE = ulink(SORTCOMPLETE, MODULENAME, supbrw)



        # get everything before the end time
        if not flsrh:
            start_dt = SRTTIME
            range_sec = 300 if THETIME == 'noarguser' else int(THETIME)
            end_dt = start_dt + timedelta(seconds=range_sec)
            lines = [entry for entry in SORTCOMPLETE if entry[0] <= end_dt]
        else:
            lines = SORTCOMPLETE


        # filter out the /tmp files
        tmp_lines = [entry for entry in lines if entry[1].startswith("/tmp")]
        non_tmp_lines = [entry for entry in lines if not entry[1].startswith("/tmp")]
        SORTCOMPLETE = non_tmp_lines
        TMPOUTPUT = tmp_lines

        filtered_lines = []
        for entry in SORTCOMPLETE:
            ts_str = entry[0]
            filepath = entry[14]
            filtered_lines.append((ts_str, filepath))
        
        TMPOPT = filtered_lines

        RECENT = TMPOPT[:]

        # Apply filter used for results, copying. RECENT unfiltered stored in db.
        TMPOPT = filter_lines_from_list(TMPOPT, USR)  
    
        if tmn:
            logf = RECENT # all files
        elif method == "rnt":
            logf = TMPOPT # filtered
        if argf == "filtered" or flsrh:
            logf = TMPOPT # filtered
            if argf == "filtered" and flsrh:
                logf = RECENT # dont filter inverse

        
        # Copy files `recentchanges` and move its searches
        validrlt = copyfiles(RECENT, RECENTNUL, TMPOPT, method, argone, argtwo, USR, mainl, archivesrh, autooutput, cmode, fmt)
        

        #Merge/Move old searches
        if SORTCOMPLETE:
            syschg=True
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
            if not OLDSORT and not flsrh  and argf != "filtered" and method != "rnt":
                fallback_path = f'/tmp/{MODULENAME}{flnm}'
                if os.path.isfile(fallback_path):
                    with open(fallback_path, 'r') as f:
                        OLDSORT = f.readlines()

            # try `recentchanges` searches /tmp/MODULENAME_MDY*
            if not OLDSORT:
                hsearch(OLDSORT, MODULENAME, argone)


            # output /tmp file results 
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
            #else:

    
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
                    isdiff(SORTCOMPLETE, ABSENT, rout, diffnm, difff_file, flsrh, SRTTIME, fmt) 
                    

            #Send search result SORTCOMPLETE to user
            with open(filepath, 'w') as f:
                for entry in logf:
                    tss = entry[0].strftime(fmt)
                    fp = entry[1]
                    f.write(f'{tss} {fp}\n')
            changeperm(filepath, uid)


            # Backend
            pstsrg.main(SORTCOMPLETE, COMPLETE, dbtarget, rout, checksum, cdiag, email, ANALYTICSECT, ps, nc, USR)

            # Diff output to user
            csum=processha.processha(rout, ABSENT, diffnm, cerr, flsrh, MODULENAME, argf, SRTTIME, USR, supbrw, supress, fmt)

            # Filter hits
            update_filter_csv(RECENT, USR, flth) 

            # Post ops
            if POSTOP:
                if syschg:

                    if method != "rnt":
                        outf=logf
                    else:
                        outf=RECENT
                    postop(outf, USRDIR, toml, fmt)


            # Terminal output process scr/cer
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
                if os.path.isfile(cerr):
                    with open(cerr, 'r') as src, open(diffnm, 'a') as dst:
                        dst.write(f"\ncdiag alert\n")
                        dst.write(src.read())     
                    removefile(cerr)

            if ANALYTICSECT:
                el = end - start  
                print(f'Search took {el:.3f} seconds')
                if checksum:
                    el = cend - cstart
                    print(f'Checksum took {el:.3f} seconds')

            try:
                logic(syschg, nodiff, diffrlt, validrlt, MODULENAME, THETIME, argone, argf, filename, flsrh, imsg, method) # feedback
                display(dspEDITOR, filepath, syschg) # open text editor?
            except Exception as e:
                print(f"Error in logic or display: {e}")

            #Cleanup
            if os.path.isfile(diffnm):
                changeperm(diffnm, uid)
            if os.path.isfile(slog):
                removefile(slog)

            if cfr:
                ctarget = dict_string(cfr)
                # # Debug: write ctarget content to a file
                # debug_file = "/tmp/ctarget_debug.txt"
                # with open(debug_file, "w", encoding="utf-8") as f:
                #     f.write(ctarget)
                # print(f"Debug: ctarget content written to {debug_file}")
                rlt = encrm(ctarget, CACHE_F, email, False, False)
                if not rlt:
                    print(f"Reencryption failed cache not saved.")


if __name__ == "__main__":
    main()
