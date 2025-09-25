# 09/24/2025           developer buddy core
import glob
import os
import psutil
import re
import subprocess
import time
import tomllib
from filter import get_exclude_patterns
from pyfunctions import cprint


# supress terminal output and hardlinks 
def sbwr(LCLMODULENAME):
    return [
        'mozilla',
        '.mozilla',
        'chromium-ungoogled',
        # 'google-chrome',
        LCLMODULENAME
    ]


# toml
def load_config(confdir):
    with open(confdir, 'rb') as f:
        config = tomllib.load(f)
    return config

# term output
def logic(syschg, samerlt, nodiff, diffrlt, validrlt, copyres,MODULENAME, THETIME, argone, argf, filename, flsrh, imsg, method):
    
    if method == "rnt":
        if validrlt == "true":
            cprint.cyan(copyres)
        elif validrlt == "nofiles":
            cprint.cyan('There were no files to grab.')
            print()

        if THETIME != "noarguser" and syschg:
            cprint.cyan("All system files in the last $THETIME seconds are included")
            
            cprint.cyan(f'{MODULENAME}xSystemchanges{argone}')
        elif syschg:
            cprint.cyan("All system files in the last 5 minutes are included")

            cprint.cyan(f'{MODULENAME}xSystemchanges{argone}')

    else:
        if flsrh:
            cprint.cyan(f'All files newer than {filename} in /Downloads')
        elif argf:
            cprint.cyan('All new filtered files are listed in /Downloads')
        else:
            cprint.cyan('All new system files are listed in /Downloads')

    if syschg:
        cprint.cyan('No sys files to report')
    if samerlt and syschg and nodiff:
        cprint.cyan('The sys search was the same as before.')
    if not diffrlt and nodiff:
        cprint.green('Nothing in the sys diff file. That is the results themselves are true.')
    if imsg:
        print(imsg)

# if [ "$syschg" == "false" ]; then  cyan "No sys files to report." ; fi
# if [ "$samerlt" == "true" ] && [ "$syschg" == "true" ] && [ "$nodiff" == "true" ]; then cyan "The sys search was the same as before." ; fi
# if [ "$diffrlt" == "false" ] && [ "$nodiff" == "true" ];then green " Nothing in the sys diff file. That is the results themselves are true" ; [[ -n "$1" ]] & cyan "$1" ; fi

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

    base_name = MODULENAME.lstrip("/")

    for suffix in suffixes:
        # Build a glob pattern that matches files starting with base_name + suffix, plus anything after
        pattern = os.path.join(USRDIR, f"{base_name}{suffix}*")
        
        # Use glob to get all matching files
        for filepath in glob.glob(pattern):
            try:
                os.remove(filepath)
                # Optional: print(f"Removed {filepath}")
            except FileNotFoundError:
                pass  # File already gone, continue

# open text editor
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


# filter files with filter.py
def filter_lines_from_list(lines, user):
    escaped_user = re.escape(user)
    regexes = [re.compile(p) for p in get_exclude_patterns(escaped_user)]
    filtered = [line for line in lines if not any(r.search(line[1]) for r in regexes)]
    return filtered


def filter_output(filepath, LCLMODULENAME, filtername, critical, pricolor, seccolor, typ, supbrwr=True, supress=False):
    webb = sbwr(LCLMODULENAME)
    flg = False

    with open(filepath, 'r') as f:
        for file_line in f:
            file_line = file_line.strip()
            ck = False

            if file_line.startswith(filtername):
                if supbrwr:
                    for item in webb:
                        if re.search(item, file_line):
                            ck = True
                            break
                if not ck and not supress and not flg:
                    getattr(cprint, pricolor, lambda msg: print(msg))(f"{file_line} {typ}")
            else:
                if critical != "no":
                    if file_line.startswith(critical) or file_line.startswith("COLLISION"):
                        getattr(cprint, seccolor, lambda msg: print(msg))(f'{file_line} {typ} Critical')
                        flg = True
                else:
                    getattr(cprint, seccolor, lambda msg: print(msg))(f"{file_line} {typ}")


# inclusions from this script
def get_runtime_exclude_list(USR, logpst, statpst, dbtarget):
    return [
        "/usr/local/save-changesnew/flth.csv",
        f"/home/{USR}/Downloads/rnt",
        logpst,
        statpst,
        dbtarget
    ]


# parsing python
#
# def read_file_lines(path):
#     p = Path(path)
#     return [line.rstrip() for line in p.open()] if p.is_file() and p.stat().st_size > 0 else []
#
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



def gettime(analytic=False, checksum=False, init="false", x=0, y=0):
    if analytic:
        x = time.time()
        if checksum:
            y = time.time()
            if init == "init":
                cprint.cyan('Running checksum.')
    
    if not y:
        return x
    return x, y

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


def openrc(log_file, CACHE_F, checksum, tout):

    inotify_processes = [proc for proc in psutil.process_iter(['pid', 'name', 'cmdline']) if 'inotify' in proc.info['cmdline']]

    if inotify_processes:
        if log_file:

            try:
                with open(log_file, "r") as f:
                    tout.extend(line.strip() for line in f if line.strip())

                os.remove(log_file)

            except Exception as e:
                print(f"Error handling {log_file} file in /tmp: {e}")

        for proc in inotify_processes:
            proc.terminate() 
            exit_code = proc.poll()
            if exit_code is not None:
                strup(log_file, CACHE_F, checksum)
    else:
        strup(log_file, CACHE_F, checksum)


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

def changeperm(filepath, uid):
    try:
        os.chown(filepath, uid, -1)
    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except Exception as e:
        print(f"chown error {filepath}: {e}")

def copyfiles(RECENT, TMPOPT, method, argone, argtwo, USR, TEMPDIR, archivesrh, cmode, fmt):
    global RECENTNUL

    if method == "rnt":

        copynewln = 'tmp_holding' # TMPOPT filtered list
        copynul = 'toutput.tmp' # tout temp file
        sortcomplete = 'list_complete_sorted.txt' # unfiltered times only
        # 
        #
        with open('/tmp/' + copynewln, 'w') as f_filtered, open('/tmp/' + copynul , 'wb') as f_tout:
            # TMPOPT
            for record in TMPOPT:
                if len(record) >= 2:

                    date = record[0].strftime(fmt)
                    field = record[1]
                    f_filtered.write(date + " " + field + '\n') 

                    # original
                    #unesc = unescf_py(field)        
                    #f_tout.write(unesc.encode('utf-8') + b'\0') # temp file tout with only \0 delim filenames
                    # V
            # TOUT - write \0 delim filenames for `recentchanges` file copying
            f_tout.write(RECENTNUL) 

        # SORTCOMPLETE - Unfiltered RECENT as "sortcomplete" for times only
        with open('/tmp/' + sortcomplete, 'w') as f:
            for record in RECENT:

                date = record[0].strftime(fmt)
                field = record[1]

                f.write(date + " " + field + '\n') #
                                                                        #
                                                                        #
        if os.path.isfile('/tmp/' + copynewln) and os.path.getsize('/tmp/' + copynewln) > 0:
            # print('sleeping two')
            # time.sleep(15)
            try:
                copyres = subprocess.run(
                    [
                        '/usr/local/save-changesnew/recentchanges',
                        str(argone),
                        str(argtwo),
                        USR,
                        TEMPDIR,
                        sortcomplete,
                        copynewln,
                        copynul,
                        str(archivesrh),
                        cmode
                    ],
                    capture_output=True,
                    text=True
                )
            
                if copyres.returncode == 7:
                    return "nofiles"
                elif copyres.returncode ==3:
                    print(f'TMPOPT,tout,SORTCOMPLETE missing exiting from recentchanges.')
                elif copyres.returncode != 0:
                    print(f'/rntfiles.xzm failed to unable to make xzm. errcode:{copyres.returncode}')
                    
                    print("STDERR:", copyres.stderr)
                else:
                    print(copyres.stdout)
                    return "true"
                    
            except Exception as e:
                print(f"Error in recentchangest: {e}")