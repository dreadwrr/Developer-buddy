# 09/17/2025           developer buddy core
import os
import psutil
import re
import subprocess
import time
import tomllib

from pyfunctions import cprint
from pyfunctions import green
from pyfunctions import sbwr
from filter import get_exclude_patterns

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
            cprint.cyan(f'All files newer than{filename} in /Downloads')
        elif argf:
            cprint.cyan('All new filtered files are listed in /Downloads')
        else:
            cprint.cyan('All new system files are listed in /Downloads')

    if syschg:
        cprint.cyan('No sys files to report')
    if samerlt and syschg and nodiff:
        cprint.cyan('The sys search was the same as before.')
    if not diffrlt and nodiff:
        green('Nothing in the sys diff file. That is the results themselves are true.')
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
    for suffix in suffixes:
        pattern = os.path.join(USRDIR, MODULENAME.lstrip("/")) + suffix
        for filename in os.listdir(USRDIR):
            if filename.startswith(MODULENAME.lstrip("/")) and suffix in filename:
                try:
                    os.remove(os.path.join(USRDIR, filename))
                except FileNotFoundError:
                    continue

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
    regexes = [re.compile(p) for p in get_exclude_patterns(user)]
    filtered = [line for line in lines if not any(r.search(line) for r in regexes)]
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
                    pricolor(f"{file_line} {typ}")
            else:
                if critical != "no":
                    if file_line.startswith(critical) or file_line.startswith("COLLISION"):
                        seccolor(f'{file_line} {typ} Critical')
                        flg = True
                else:
                    seccolor(f"{file_line} {typ}")


# inclusions from this script
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

