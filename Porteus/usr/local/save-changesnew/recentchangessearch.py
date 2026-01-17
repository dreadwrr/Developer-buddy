#!/usr/bin/env python3
# entry point for recentchanges.                     v5.0                                                       01/13/2026
#
#   recentchanges. aka Developer buddy      recentchanges / recentchanges search
#   Provide ease of pattern finding ie what files to block we can do this a number of ways
#   1) if a file was there (many as in more than a few) and another search lists them as deleted its either a sys file or not but unwanted nontheless
#   2) Is a system file inherent to the specifc platform
#   3) intangibles ie trashed items that may pop up infrequently and are not known about
#
#   recentchanges
#           Searches are saved in /tmp and also makes rntfiles.xzm
#
#           1. Search results are unfiltered and copied files for the .xzm are from a filter.
#           2. No /tmp files displayed for clear easy to read results. Too much information makes it more difficult to interpret
#           3. 'rnt' shortcut for the same command. Unlike recentchanges search command does not inverse
#
#           The purpose of this script is to save files ideally less than 5 minutes old. So when compiling or you dont know where some files are
#   or what changed on your system. So if you compiled something you call this script to build a module of it for distribution. If not using for developing
#   call it a file change snapshot
#   We use the find command to list all files 5 minutes or newer. Filter it and then get to copying the files in a temporary staging directory.
#   Then take those files and make an .xzm. It will be placed in   /tmp  along with a transfer log to staging directory and file manifest of the xzm
#
#   recentchanges search
#           Searches are saved in /home/{user}/Downloads includes /tmp files in a seperate file
#
#           1. The search is unfiltered and a filesearch is filtered.
#           2. `rnt search` is a shortcut and inverses the results. For search it will filter the results instead of being unfiltered. For a file search it removes the filter instead as its normally filtered.
#
# Old searches can be grabbed from /Downloads, /tmp or /tmp/{MODULENAME}_MDY_*. the limit is set by archivesrh in config.toml. This is  for convenience if there is no previous search  it displays the
# old search for specified search criteria. all searches are stored in the database before applying filter.py so all data is captured
#
# borrowed script features from various scripts on porteus forums
import logging
import os
import re
import sys
import processha
import pstsrg
import signal
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from dirwalkerfnts import get_base_folders
from filterhits import update_filter_csv
from processha import isdiff
from recentchangessearchparser import build_parser
from rntchangesfunctions import clear_logs, porteus_linux_check
from rntchangesfunctions import convertn
from rntchangesfunctions import decr_ctime
from rntchangesfunctions import copy_files
from rntchangesfunctions import encrm
from rntchangesfunctions import filter_lines_from_list
from rntchangesfunctions import filter_output
from rntchangesfunctions import find_files
from rntchangesfunctions import get_runtime_exclude_list
from rntchangesfunctions import hsearch
from rntchangesfunctions import init_recentchanges
from rntchangesfunctions import intst
from rntchangesfunctions import logic
from rntchangesfunctions import removefile
from rntchangesfunctions import postop
from rntchangesfunctions import update_toml_setting
from pyfunctions import cprint
from pyfunctions import dict_to_list_sys
from pyfunctions import dict_string
from pyfunctions import get_wdir
from pyfunctions import lcl_config
from pyfunctions import load_config
from pyfunctions import setup_logger
from pyfunctions import unescf_py


# Globals
stopf = False
is_mcore = False


def sighandle(signum, frame):
    global stopf
    global is_mcore
    if signum == 2:
        stopf = True
        if is_mcore:
            print("Sending stop request")
        else:
            print("Exit on ctrl-c")
            sys.exit(0)
        # sys.exit()  # ctrl-c


signal.signal(signal.SIGINT, sighandle)
signal.signal(signal.SIGTERM, sighandle)


def main(argone, argtwo, USR, pwrd, argf="bnk", method=""):

    if argf != "bnk" and argf != "filtered" and argf != "":
        print("please call from recentchanges")
        sys.exit(0)
    if method != "rnt" and argone.lower() != "search":
        print("exiting not a search")
        sys.exit(0)

    global is_mcore

    # If not started from /usr/local/bin/recentchanges it can mess up the .gpg ownership.
    # as query is run non-root and this script is run as root. abort  <---
    caller_script = Path(sys.argv[0]).resolve()
    launcher = os.path.basename(caller_script)
    if str(launcher) != "rntchanges.py":
        print("please call from recentchanges in /usr/local/bin")
        sys.exit(0)

    appdata_local = get_wdir()  # appdata software install aka workdir used for setup_logger

    inotify_creation_file = Path("/tmp/file_creation_log.txt")
    log_path = appdata_local / "logs" / "errs.log"
    file_out = appdata_local / "file_output"
    flth_frm = appdata_local / "flth.csv"  # filter hits
    dbtarget_frm = appdata_local / "recent.gpg"
    CACHE_F_frm = appdata_local / "ctimecache.gpg"
    flth = str(flth_frm)
    dbtarget = str(dbtarget_frm)
    CACHE_F = str(CACHE_F_frm)

    toml_file, home_dir, uid, gid = lcl_config(USR, appdata_local)
    config = load_config(toml_file)
    FEEDBACK = config['analytics']['FEEDBACK']
    ANALYTICSECT = config['analytics']['ANALYTICSECT']
    email = config['backend']['email']
    checksum = config['diagnostics']['checkSUM']
    cdiag = config['diagnostics']['cdiag']
    supbrw = config['diagnostics']['supbrw']
    supress = config['diagnostics']['supress']
    POSTOP = config['diagnostics']['POSTOP']
    ps = config['diagnostics']['proteusSHIELD']  # proteus shield
    updatehlinks = config['diagnostics']['updatehlinks']
    compLVL = config['logs']['compLVL']
    MODULENAME = config['paths']['MODULENAME']     # file label
    mMODE = config['search']['mMODE']
    archivesrh = config['search']['archivesrh']
    autooutput = config['search']['autooutput']
    xzmname = config['search']['xzmname']
    cmode = config['search']['cmode']
    EXCLDIRS = config['search']['EXCLDIRS']
    ll_level = config['search']['logLEVEL']
    xRC = config['search']['xRC']

    if mMODE == "mc":
        is_mcore = True

    escaped_user = re.escape(USR)

    TMPOUTPUT = []  # holding
    # Searches
    RECENT = []  # main results
    tout = []  # ctime results
    SORTCOMPLETE = []  # combined
    TMPOPT = []   # combined filtered
    # NSF
    COMPLETE_1 = []
    COMPLETE_2 = []
    COMPLETE = []   # combined
    # Diff file
    difff_file = []
    ABSENT = []  # actions
    rout = []  # actions from ha

    cfr = {}  # cache dict
    RECENTNUL = b""  # filepaths `recentchanges`

    start = 0
    end = 0
    cstart = 0
    cend = 0

    ag = 0

    validrlt = tmn = filename = search_time = search_paths = None
    diffrlt = False
    nodiff = False
    syschg = False
    flsrh = False
    is_porteus = True
    dcr = True  # means to leave open after encrypting

    flnm = ""
    parseflnm = ""
    diffnm = ""

    filepath = ""
    DIRSRC = ""

    tsv_doc = "doctrine.tsv"
    fmt = "%Y-%m-%d %H:%M:%S"

    USRDIR = os.path.join(home_dir, "Downloads")
    if USR == "root":
        os.makedirs(USRDIR, mode=0o755, exist_ok=True)

    basedir = "/"
    # after default exclusions the following are left: "/bin", "/etc", "/home", "/lib", "/lib64", "/opt", "/root", "/sbin", "/tmp", "/usr",  "/var"
    F = [
        "find",
        basedir
    ]

    search_list = []
    try:
        # dynamic directory exclusion
        PRUNE = ["("]
        for i, d in enumerate(EXCLDIRS):
            PRUNE += ["-path", os.path.join(basedir, d.replace('$', '\\$'))]
            if i < len(EXCLDIRS) - 1:
                PRUNE.append("-o")
        PRUNE += [")", "-prune",  "-o"]

        # The main search operates on excluded folders from config.toml.
        # To build the folders that are searched and output that to the user:
        EXCLDIRS_FULLPATH = [os.path.join(basedir, d) for d in EXCLDIRS]
        base_folders, _ = get_base_folders(basedir, EXCLDIRS_FULLPATH)
        for folder in base_folders:
            if folder == "/":
                continue
            search_list.append(folder)

    except Exception as e:
        print("Problem with EXCLDIRS list. using default search. check EXCLDIRS setting", toml_file)
        print("Error: ", e)
        F = [
            "find",
            "/bin", "/etc", "/home", "/lib", "/lib64", "/opt", "/root", "/sbin", "/tmp", "/usr",  "/var"
        ]
        PRUNE = []
        search_list = []

    TAIL = ["-not", "-type", "d", "-printf", "%T@ %A@ %C@ %i %M %n %s %u %g %m %p\\0"]

    TEMPD = tempfile.gettempdir()

    with tempfile.TemporaryDirectory(dir=TEMPD) as mainl:

        scr = os.path.join(mainl, "scr")  # feedback
        cerr = os.path.join(mainl, "cerr")  # priority

        logging_values = (appdata_local, ll_level, mainl)
        setup_logger(logging_values[1], "MAIN", logging_values[0])

        if ll_level == "DEBUG":
            cprint.cyan(f"Debug logging to log_file: {str(logging_values[0])}")

        start = time.time()

        cfr = decr_ctime(CACHE_F)

        # load ctime or files created or copied with preserved metadata
        # #
        tout = init_recentchanges(appdata_local, inotify_creation_file, cfr, xRC, checksum, updatehlinks, MODULENAME, logging_values[0])

        if argone != "search":
            THETIME = argone
        else:
            THETIME = argtwo

        if THETIME != "noarguser":
            p = 60
            try:
                argone = int(THETIME)
                tmn = convertn(argone, p, 2)
                search_time = tmn
                cprint.cyan(f"Searching for files {argone} seconds old or newer")

            except ValueError:  # its a file search

                argone = ".txt"
                if not os.path.isdir(pwrd):
                    print(f'Invalid argument {pwrd}. PWD required.')
                    sys.exit(1)
                os.chdir(pwrd)

                filename = argtwo

                if not os.path.isfile(filename) and not os.path.isdir(filename):
                    print('No such directory, file, or integer.')
                    sys.exit(1)

                parseflnm = os.path.basename(filename)
                if not parseflnm:  # get directory name
                    parseflnm = filename.rstrip('/').split('/')[-1]

                cprint.cyan(f"Searching for files newer than {filename}")
                flsrh = True
                ct = int(time.time())
                frmt = int(os.stat(filename).st_mtime)
                ag = ct - frmt
                ag = convertn(ag, p, 2)
                search_time = ag
                # mmin = ["-newer", f"{filename}"]  # original  or mmin = ["-mmin", f"-{search_time}"]
                # cmin = ["-cmin", f"-{ag}"]

        else:
            tmn = search_time = argone = 5
            cprint.cyan('Searching for files 5 minutes old or newer')

        # Main search

        current_time = datetime.now()
        search_start_dt = (current_time - timedelta(minutes=search_time))

        # bypass ctime loop
        if tout:
            mmin = ["-mmin", f"-{search_time}"]
            if search_list:
                search_paths = 'Running command:' + ' '.join(["find"] + search_list + mmin + TAIL)

            find_command_mmin = F + PRUNE + mmin + TAIL
            init = True
            RECENT, COMPLETE_1, RECENTNUL, end, cstart = find_files(find_command_mmin, search_paths, mMODE, "mtime", RECENT, COMPLETE_1, RECENTNUL, init, checksum, updatehlinks, cfr, FEEDBACK, search_start_dt, logging_values, end, cstart)  # bypass ctime loop if xRC
        # standard execution
        else:
            cmin = ["-cmin", f"-{search_time}"]
            current_time = datetime.now()
            if search_list:
                search_paths = 'Running command:' + ' '.join(["find"] + search_list + cmin + TAIL)

            find_command_cmin = F + PRUNE + cmin + TAIL
            init = True
            tout, COMPLETE_2, RECENTNUL, end, cstart = find_files(find_command_cmin, search_paths, mMODE, "ctime", tout, COMPLETE_2, RECENTNUL, init, checksum, updatehlinks, cfr, FEEDBACK, search_start_dt, logging_values, end, cstart)
            cmin_end = time.time()
            cmin_start = current_time.timestamp()
            cmin_offset = convertn(cmin_end - cmin_start, 60, 2)

            mmin = ["-mmin", f"-{search_time + cmin_offset:.2f}"]
            if search_list:
                search_paths = 'Running command:' + ' '.join(["find"] + search_list + mmin + TAIL)
            find_command_mmin = F + PRUNE + mmin + TAIL
            init = False
            RECENT, COMPLETE_1, RECENTNUL, end, cstart = find_files(find_command_mmin, search_paths, mMODE, "mtime", RECENT, COMPLETE_1, RECENTNUL, init, checksum, updatehlinks, cfr, FEEDBACK, search_start_dt, logging_values, end, cstart)
        cend = time.time()
        # end Main search

        if stopf:
            print("Exit on ctrl-c")
            sys.exit(0)
        if RECENT:
            if cfr:
                data_to_write = dict_to_list_sys(cfr)
                ctarget = dict_string(data_to_write)

                nc = intst(CACHE_F, compLVL)
                rlt = encrm(ctarget, CACHE_F, email, no_compression=nc, armor=False)
                if not rlt:
                    print("Reencryption failed cache not saved.")
        else:
            cprint.cyan("No files found or invalid search criteria ")
            return 0

        COMPLETE = COMPLETE_1 + COMPLETE_2  # nsf append to rout in pstsrg before stat insert

        SORTCOMPLETE = RECENT

        # get everything from the start time

        SORTCOMPLETE.sort(key=lambda x: x[0])

        SRTTIME = SORTCOMPLETE[0][0]

        merged = SORTCOMPLETE[:]

        for entry in tout:
            if not entry:
                continue
            tout_dt = entry[0]
            if tout_dt >= SRTTIME:
                merged.append(entry)
        merged.sort(key=lambda x: x[0])

        # the start time is stored before appending ctime results
        seen = {}

        for entry in merged:
            if len(entry) < 11:
                continue
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
        exclude_patterns = get_runtime_exclude_list(USRDIR, log_path, MODULENAME, flth, dbtarget, CACHE_F)

        def filepath_included(filepath, exclude_patterns):
            filepath = filepath.lower()
            return not any(filepath.startswith(p.lower()) for p in exclude_patterns)

        SORTCOMPLETE = [
            entry for entry in deduped
            if filepath_included(entry[1], exclude_patterns)
        ]
        # for feedback in proper location
        if updatehlinks:
            cprint.green('Updating hardlinks')

        # get everything before the end time to exclude weird files created in the future. Doesnt happen on windows **
        if not flsrh:
            start_dt = SRTTIME
            range_sec = 300 if THETIME == 'noarguser' else int(THETIME)
            end_dt = start_dt + timedelta(seconds=range_sec)
            lines = [entry for entry in SORTCOMPLETE if entry[0] <= end_dt]
        else:
            lines = SORTCOMPLETE

        # with open("/home/guest/martar3", 'w') as f:
        #    for entry in SORTCOMPLETE:
        #        tss = entry[0].strftime(fmt)
        #        fp = entry[1]
        #        f.write(f'{tss} {fp}\n')

        # filter out the /tmp files
        # remove all tmp folders if it is `recentchanges` or method "rnt". if it is `recentchanges search` or method "" put them in a seperate file
        # temp = tempfile.gettempdir()
        # another temp directories ie ('/tmp', temp)
        patterns = tuple(p for p in ('/tmp',) if isinstance(p, str) and p)
        tmp_lines = []         # amended from original
        non_tmp_lines = []      # .

        # filter out the Temp files
        for entry in lines:
            if entry[1].startswith(patterns):
                tmp_lines.append(entry)
            else:
                non_tmp_lines.append(entry)

        # tmp_lines = [entry for entry in lines if entry[1].startswith("/tmp")]  # original
        # non_tmp_lines = [entry for entry in lines if not entry[1].startswith("/tmp")]

        SORTCOMPLETE = non_tmp_lines
        TMPOUTPUT = tmp_lines

        filtered_lines = []
        for entry in SORTCOMPLETE:
            ts_str = entry[0]
            filepath = entry[14]
            filtered_lines.append((ts_str, filepath))

        TMPOPT = filtered_lines

        RECENT = TMPOPT[:]

        # with open("/home/guest/martar2", 'w') as f:
        #    for entry in TMPOPT:
        #        tss = entry[0].strftime(fmt)
        #        fp = entry[1]
        #        f.write(f'{tss} {fp}\n')

        # Apply filter used for results, copying. RECENT unfiltered stored in db.
        TMPOPT = filter_lines_from_list(TMPOPT,  escaped_user)

        logf = []
        logf = RECENT
        if tmn:
            logf = RECENT  # all files
        if method != "rnt":
            if argf == "filtered" or flsrh:
                logf = TMPOPT  # filtered
                if argf == "filtered" and flsrh:
                    logf = RECENT   # all files. dont filter inverse

        # Copy files `recentchanges` and move old searches if it is not porteus bypass. If cant tell distro run normally, copy is bypassed in called script if not porteus but it
        # still moves the old files
        if method == 'rnt':
            if stopf:
                print("Exit on ctrl-c")
                sys.exit(0)
            res = porteus_linux_check()
            if res:
                validrlt = copy_files(RECENT, RECENTNUL, TMPOPT, argone, THETIME, argtwo, USR, mainl, archivesrh, autooutput, xzmname, cmode, fmt, appdata_local)
            elif res is not None:
                is_porteus = False
            else:
                validrlt = copy_files(RECENT, RECENTNUL, TMPOPT, argone, THETIME, argtwo, USR, mainl, archivesrh, autooutput, xzmname, cmode, fmt, appdata_local)

        # Merge/Move old searches
        if SORTCOMPLETE:
            syschg = True
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
                DIRSRC = "/tmp"  # 'recentchanges'
                if not is_porteus:
                    validrlt = clear_logs(USRDIR, DIRSRC, 'rnt', '/tmp', MODULENAME, archivesrh)
            else:
                DIRSRC = USRDIR  # 'search'

            # is old search?
            result_output = os.path.join(DIRSRC, f'{MODULENAME}{flnm}')

            if os.path.isfile(result_output):
                with open(result_output, 'r') as f:
                    OLDSORT = f.readlines()

            # try /tmp for previous search
            if not OLDSORT and not flsrh and argf != "filtered" and method != "rnt":
                fallback_path = f'/tmp/{MODULENAME}{flnm}'
                if os.path.isfile(fallback_path):
                    with open(fallback_path, 'r') as f:
                        OLDSORT = f.readlines()

            # try `recentchanges` searches /tmp/MODULENAME_MDY*
            if not OLDSORT and not flsrh and argf != "filtered":
                hsearch(OLDSORT, MODULENAME, argone)

            target_path = None
            # output /tmp file results
            if method != "rnt":
                # Reset. move old searches
                validrlt = clear_logs(USRDIR, DIRSRC, method, '/tmp', MODULENAME, archivesrh)
                # send /tmp results to user
                if TMPOUTPUT:
                    b_argone = '' if parseflnm.endswith('.txt') else str(argone)
                    target_filename = f"{MODULENAME}xSystemTmpfiles{parseflnm}{b_argone}"
                    target_path = os.path.join(USRDIR, target_filename)
                    with open(target_path, 'w') as dst:
                        for entry in TMPOUTPUT:
                            tss = entry[0].strftime(fmt)
                            fp = entry[1]
                            dst.write(f'{tss} {fp}\n')

            diffnm = os.path.join(DIRSRC, MODULENAME + flnmdff)

            # Difference file
            if OLDSORT:
                nodiff = True

                clean_oldsort = [line.strip() for line in OLDSORT]
                clean_logf_set = set(f'{entry[0].strftime(fmt)} {entry[1]}' for entry in logf)
                difff_file = [line for line in clean_oldsort if line not in clean_logf_set]

                if difff_file:
                    diffrlt = True
                    removefile(diffnm)
                    with open(diffnm, 'w') as file2:
                        for entry in difff_file:
                            print(entry, file=file2)
                        file2.write("\n")

                    # preprocess before db/ha. The differences before ha and then sent to processha after ha
                    isdiff(SORTCOMPLETE, ABSENT, rout, diffnm, difff_file, flsrh, SRTTIME, fmt)

            # Send search result SORTCOMPLETE to user
            removefile(result_output)
            with open(result_output, 'w') as f:
                for entry in logf:
                    tss = entry[0].strftime(fmt)
                    fp = entry[1]
                    f.write(f'{tss} {fp}\n')

            # Backend
            if stopf:
                print("Exit on ctrl-c")
                sys.exit(0)
            res = pstsrg.main(dbtarget, SORTCOMPLETE, COMPLETE, logging_values, rout, scr, cerr, mMODE, checksum, cdiag, email, ANALYTICSECT, ps, compLVL, USR, dcr)
            #  dbopt = res  # alternatively return dbopt filename if doing something after with .db then remove in cleanup
            if res is not None:
                if res == 0 or res == "new_profile":
                    if os.path.isfile(dbtarget):
                        os.chown(dbtarget, uid, gid)
                        # os.chmod(dbtarget, 0o600)
                # elif res == 3:
                #     print("Encryption error")
                # elif res == 4:
                #     print("Db error")
                # elif res != 0:
                #     print("Other problem: error: ", res)
                # elif res == 0:

            if ANALYTICSECT:
                el = end - start
                print(f'Search took {el:.3f} seconds')
                if checksum:
                    el = cend - cstart
                    print(f'Checksum took {el:.3f} seconds')

            # Diff output to user
            csum = processha.processha(rout, ABSENT, diffnm, cerr, flsrh, argf, SRTTIME, escaped_user, supbrw, supress)

            # Filter hits
            update_filter_csv(RECENT, USR, flth)

            # Post ops
            if POSTOP and not stopf:

                try:

                    if syschg:
                        outpath = os.path.join(USRDIR, tsv_doc)
                        if not os.path.isfile(outpath):

                            # Check if it was a copy
                            copy_paths = set()
                            if rout:
                                for line in rout:
                                    parts = line.strip().split(maxsplit=5)
                                    if len(parts) < 6:
                                        continue
                                    action = parts[0]
                                    if action in ("Deleted", "Nosuchfile"):
                                        continue
                                    if action == "Copy":
                                        full_path = unescf_py(parts[5])
                                        copy_paths.add(full_path)

                            all_data = []
                            for record in SORTCOMPLETE:

                                if len(record) < 16:
                                    logging.debug("An entry for POSTOP was short less than 16. record: %s", record)
                                    continue

                                mtime = record[0].strftime(fmt)  # 1 2
                                changetime = record[2] if record[2] else "None None"  # 3 4
                                atime = record[4] if record[4] else "None None"  # 5 6
                                filesize = record[6]  # 7
                                sym = record[7]  # 8
                                user = record[8]  # 9
                                group = record[9]  # 10
                                cam = record[11]  # 11
                                lastmodified = record[12] if record[12] else "None None"    # 12 13
                                is_copy = "y" if record[14] in copy_paths else "None"       # 14
                                file_path = record[14]                                      # 15
                                # inode = record[3]
                                # checksum = record[5]
                                # mode = record[10]
                                # hardlink = record[13]
                                # usec_zero = record[15]
                                all_data.append((mtime, changetime, atime, filesize, sym, user, group, cam, lastmodified, is_copy, file_path))

                            if method != "rnt":
                                if logf is TMPOPT:
                                    all_data = filter_lines_from_list(all_data, escaped_user, idx=10)

                            postop(all_data, USRDIR, toml_file, appdata_local)
                            # cprint.green(f"File doctrine.tsv created {USRDIR}\\{tsv_doc}")
                            if os.path.isfile(outpath):
                                os.chown(outpath, uid, gid)
                                # os.chmod(outpath, 0o600)
                        else:
                            update_toml_setting('diagnostics', "POSTOP", False, toml_file)
                            # update_config(toml_file, "POSTOP", "true", quiet=True)  # avoid spawning process

                except Exception as e:
                    logging.error(f"Error in POSTOP. err: {e} {type(e).__name__}", exc_info=True)

            # Terminal output process scr/cer
            if not csum and not supress:
                if os.path.exists(scr):
                    filter_output(scr, escaped_user, 'Checksum', 'no', 'blue', 'yellow', 'scr', supbrw)

            if csum:
                if os.path.isfile(cerr):
                    with open(cerr, 'r') as src, open(diffnm, 'a') as dst:
                        dst.write("\ncerr\n")
                        for line in src:
                            if line.startswith("Warning File"):
                                continue
                            dst.write(line)
                    removefile(cerr)

            try:
                logic(syschg, nodiff, diffrlt, validrlt, MODULENAME, THETIME, argone, argf, filename, flsrh, method)  # feedback
                # display(dspEDITOR, result_output, syschg, dspPATH)  # open text editor?  commented out for wayland to open results in /usr/local/bin/recentchanges non-root
            except Exception as e:
                print(f"Error in logic or display: {e}")

            # Cleanup
            if os.path.isfile(scr):
                removefile(scr)

            if target_path and os.path.isfile(target_path):
                os.chown(target_path,  uid, gid)
                # os.chmod(target_path, 0o600)
            if os.path.isfile(diffnm):
                os.chown(diffnm, uid, gid)
                # os.chmod(diffnm, 0o600)
            if os.path.isfile(flth):
                os.chown(flth, uid, gid)
                # os.chmod(flth, 0o600)

            # write search file location to open as non root
            if os.path.isfile(result_output):
                os.chown(result_output, uid, gid)
                # os.chmod(result_output, 0o600)

                with open(file_out, 'w') as f1:
                    f1.write(result_output)
                if file_out.is_file():
                    os.chown(file_out, uid, gid)

            if syschg and os.path.isfile(result_output) and os.path.getsize(result_output) != 0:
                return 0
        return 1


def main_entry(argv):
    parser = build_parser()
    args = parser.parse_args(argv)

    calling_args = [
        args.argone,
        args.argtwo,
        args.USR,
        args.PWD,
        args.argf,
        args.method
    ]

    sys.exit(main(*calling_args))
