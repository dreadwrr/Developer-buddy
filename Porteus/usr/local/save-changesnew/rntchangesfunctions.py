# developer buddy v5.0 core                     original 09/26/2025 updated 01/13/2026
import glob
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from configfunctions import update_config
from filter import get_exclude_patterns
from fsearch import process_lines
from pyfunctions import cprint
from pyfunctions import suppress_list
from pyfunctions import unescf_py

# 02/26/2026

# Note: For database cacheclear / terminal supression see pyfunctions.py


# Globals
QUOTED_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


# file operations

def name_of(locale, ext=''):
    f_name = os.path.basename(locale)
    root, _ = os.path.splitext(f_name)
    return root + ext


def change_perm(path, uid, gid=None, mode=0o644):
    try:
        os.chown(path, uid, gid if gid is not None else -1)
        if mode is not None:
            os.chmod(path, mode)
    except FileNotFoundError:
        # print(f"File not found: {path}")
        pass
    except PermissionError:
        print(f"Permission error {path}")
    except Exception as e:
        print(f"chown/chmod error {path}: {e}")


def removefile(fpath):
    try:
        if os.path.isfile(fpath):
            os.remove(fpath)
        return True
    except (TypeError, FileNotFoundError):
        pass
    except Exception:
        # print(f'Problem removing {fpath}: {e}')
        pass
    return False


# inclusions from this script
def get_runtime_exclude_list(USRDIR, MODULENAME, user, file_out, flth, dbtarget, CACHE_F, log_path, dbopt=None, temp_dir=None):

    # tmp_results = os.path.join("/tmp", MODULENAME)
    download_results = os.path.join(USRDIR, f'{MODULENAME}x')
    gnupg_one = f"/home/{user}/.gnupg/random_seed"
    gnupg_two = "/root/.gnupg/random_seed"

    excluded_list = [
        download_results,
        gnupg_one,
        gnupg_two,
        flth,
        dbtarget,
        CACHE_F,
        log_path
    ]
    if dbopt:
        excluded_list += [dbopt]
    if temp_dir:
        excluded_list += [temp_dir]
    # dir_pth = os.path.join("/tmp", "MDY_*")
    # folders = glob.glob(dir_pth)
    # old_searches = [os.path.join(fld, MODULENAME) for fld in folders]
    # for entry in old_searches:
    #     excluded_list.append(entry)
    return excluded_list


# Initialize
def cnc(target_file, compLVL):
    CSZE = 1024*1024
    if os.path.isfile(target_file):
        _, ext = os.path.splitext(target_file)
        try:
            file_size = os.stat(target_file).st_size
            size = file_size
            if ext == ".gpg":
                size = file_size // 2

            return size // CSZE >= compLVL  # no compression
        except Exception as e:
            print(f"Error setting compression of {target_file}: {e}")
    return False


def check_stop(stopf):
    if stopf:
        print("Exit on ctrl-c", flush=True)
        sys.exit(0)


# term output
def logic(syschg, nodiff, diffrlt, validrlt, THETIME, argone, argf, result_output, filename, flsrh, method):

    if syschg:
        # if validrlt == "prev":
        #     print("Refer to /rntfiles_MDY folder for the previous search")

        if method == "rnt":

            if validrlt == "nofiles":
                cprint.cyan('There were no files to grab.')
                print()

            if THETIME != "noarguser":
                cprint.cyan(f'All system files in the last {argone} seconds are included')

            else:
                cprint.cyan("All system files in the last 5 minutes are included")

        else:

            if flsrh:
                cprint.cyan(f'All files newer than {filename} in /Downloads')
            elif argf:
                cprint.cyan('All new filtered files are listed in /Downloads')
            else:
                cprint.cyan('All new system files are listed in /Downloads')
        cprint.cyan(result_output)

    else:
        cprint.cyan('No sys files to report')
    if not diffrlt and nodiff:
        cprint.green('Nothing in the sys diff file. That is the results themselves are true.')


# dspEDITOR disabled and results opened in bash wrapper /usr/local/bin/recentchanges to not run query or editor as root **
# open text editor   # Resource leaks   wait() commun
def display(dspEDITOR, filepath, syschg, dspPATH):
    if not (dspEDITOR and dspPATH):
        return
    if not syschg:
        # print(f"No file to open with {dspEDITOR}: {filepath}")
        return

    if os.path.isfile(filepath):  # and os.path.getsize(filepath) != 0:
        try:
            subprocess.Popen([dspPATH, filepath])  # , shell=True windows **
        except Exception as e:
            print(f"{dspEDITOR} failed. Try setting abs editor path (dspPATH). Error: {e}")


def resolve_editor(dspEDITOR, dspPATH, toml_file):

    EDITOR_MAP = {
        "xed": r"/usr/bin/xed",
        "featherpad": r"/usr/bin/featherpad"
    }

    display_editor = dspEDITOR

    def get_editor_path(editor_key, dspPATH):
        if dspPATH:
            return dspPATH
        return EDITOR_MAP.get(editor_key.lower())

    def validate_editor(editor_path, editor_key, dspPATH):
        if os.path.isfile(editor_path):
            return True
        if dspPATH:
            print(f"{editor_key} dspPATH incorrect: {dspPATH}")
        elif editor_path is not None:
            print(f"{editor_key} not installed (expected: {editor_path})")
        elif not editor_path:
            print(f"Invalid value for dspEDITOR {dspEDITOR}")
        return False

    editor_key = dspEDITOR.lower()
    editor_path = None

    if editor_key == "featherpad" and not dspPATH:
        editor_path = shutil.which("featherpad")
    elif editor_key == "xed" and not dspPATH:
        editor_path = shutil.which("xed")

    if not editor_path:

        editor_path = get_editor_path(editor_key, dspPATH)
        if not editor_path:
            if dspPATH:
                print(f"Invalid path {dspPATH} for setting dspPATH")
                sys.exit(1)
            print(f"{dspEDITOR} not found please specify a dspPATH or path to an editor in settings")

        if not validate_editor(editor_path, editor_key, dspPATH):
            display_editor = False
            print(f"Couldnt find {dspEDITOR} in path. continuing without editor")
            update_config(toml_file, "dspEDITOR", "true")
            editor_path = ""

    return display_editor, editor_path
# end dspEDITOR disabled


def is_excluded(web_list, file_line):
    return any(re.search(pat, file_line) for pat in web_list)


def is_supressed(web_list, file_line, flg, suppress_browser, supress):
    if flg or supress:
        return True
    if suppress_browser and web_list:
        return is_excluded(web_list, file_line)
    return False


# scr / cerr logic
def filter_output(filepath, escaped_user, filtername, critical, pricolor, seccolor, typ, suppress_browser=True, supress=False):
    web_list = suppress_list(escaped_user)
    flg = False
    with open(filepath, 'r') as f:
        for file_line in f:

            file_line = file_line.strip()
            if file_line.startswith(filtername):

                if not is_supressed(web_list, file_line, flg, suppress_browser, supress):
                    getattr(cprint, pricolor, lambda msg: print(msg))(f"{file_line} {typ}")
            else:
                if critical != "no":
                    if file_line.startswith(critical) or file_line.startswith("COLLISION"):
                        getattr(cprint, seccolor, lambda msg: print(msg))(f'{file_line} {typ} Critical')
                        flg = True
                else:
                    if not is_supressed(web_list, file_line, flg, suppress_browser, supress):
                        getattr(cprint, seccolor, lambda msg: print(msg))(f"{file_line} {typ}")
    return flg


def porteus_linux_check():
    if os.path.isfile("/etc/porteus-release"):
        return True
    os_release_path = "/etc/os-release"
    distro_info = {}
    try:
        with open(os_release_path, "r") as file:
            for line in file:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    value = value.strip('"')
                    distro_info[key] = value
        distro_id = distro_info.get("ID", "").lower()
        distro_name = distro_info.get("NAME", "").lower()
        for target in ("porteus", "nemesis"):
            if target in distro_id or target in distro_name:
                return True
        return False
    except FileNotFoundError:
        print("The file /etc/os-release was not found.")
    except Exception as e:
        print(f'An error occurred: {e}')
    return None


# One search ctime > mtime for downloaded, copied or preserved metadata files. cmin. Main search for mtime newer than mmin.
def find_files(find_command, search_paths, file_type, RECENT, COMPLETE, RECENTNUL, init, cfr, search_start_dt, user_setting, logging_values, end, cstart, logger=None):
    file_entries = []

    table = "logs"

    if search_paths:
        print(search_paths)
    else:
        print('Running command:', ' '.join(find_command))

    try:

        proc = subprocess.Popen(find_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # stderr=subprocess.DEVNULL
        output, err = proc.communicate()

        if proc.returncode not in (0, 1):
            stderr_str = err.decode("utf-8")
            print(stderr_str)
            print("Find command failed, unable to continue. Quitting.")
            sys.exit(1)

    except (FileNotFoundError, PermissionError) as e:
        print(f"Error running find in find_files {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error running find ommand: {find_command} \nfind_files func: {type(e).__name__} {e}")
        sys.exit(1)

    if file_type == "main":
        end = time.time()

    file_entries = [entry.decode('utf-8', errors='backslashreplace') for entry in output.split(b'\0') if entry]

    # using escf_py and unesc_py for bash support otherwise can use: filename.encode('unicode_escape').decode('ascii') , codecs.decode(escaped, 'unicode_escape')
    # using escf_py and unesc_py for bash
    # filename.encode('unicode_escape').decode('ascii') \n -> \\n \t -> \\t \r -> \\r  \ -> \\  é -> \xe9 not  $ " '
    # codecs.decode(escaped.encode('ascii'), 'unicode_escape')
    # json.dumps(filename)    " -> \"   \n -> \\n   \ -> \\   \t -> \\t  \r \\r
    # json.loads(line)

    records = []
    for entry in file_entries:
        fields = entry.split(maxsplit=10)
        if len(fields) >= 11:
            if file_type == "main":
                file_path = fields[10]
                RECENTNUL += (file_path.encode() + b'\0')  # copy file list `recentchanges` null byte
                if user_setting['FEEDBACK']:  # scrolling terminal look       alternative output
                    print(fields[10])

            # escaped_entry = " ".join(fields)
            records.append(fields)

    if file_type not in ("ctime", "main"):
        raise ValueError(f"Invalid search type: {file_type}")

    if init and user_setting['checksum']:
        cstart = time.time()
        cprint.cyan("Running checksum")
    RECENT, COMPLETE = process_lines(records, file_type, table, search_start_dt, 'FSEARCH', user_setting, logging_values, cfr)

    return RECENT, COMPLETE, RECENTNUL, end, cstart


# recentchanges search
# after checking for a previous search it is required to remove all old searches to prevent write problems of the results
# also keeping the workspace clean as its important to have the exact number of files. This will erase all types and
# achieve this result. Also copy the old search to the MDY folder in app install for later diff retention
def clear_logs(USRDIR, DIRSRC, method, appdata_local, MODULENAME, archivesrh):

    FLBRAND = datetime.now().strftime("MDY_%m-%d-%y-TIME_%H_%M_%S")  # %y-%m-%d better sorting?
    validrlt = ""

    # Archive last search to /tmp
    keep = [
        "xSystemchanges",
        "xSystemDiffFromLastSearch"
    ]

    new_folder = None
    for suffix in keep:
        pattern = os.path.join(DIRSRC, f"{MODULENAME}{suffix}*")
        matches = glob.glob(pattern)
        for fp in matches:
            if not new_folder:
                validrlt = "prev"  # mark as not first time search
                new_folder = os.path.join(appdata_local, f"{MODULENAME}_{FLBRAND}")
                Path(new_folder).mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(fp, new_folder)
            except Exception as e:
                print(f'clear_logs func Failed to move {fp} to appdata: {e}')

    if validrlt == "prev":
        # Delete oldest dir
        pattern = os.path.join(appdata_local, f"{MODULENAME}_MDY_*")

        dirs = glob.glob(pattern)
        dirs = [d for d in dirs if os.path.isdir(d)]

        dirs.sort()
        while len(dirs) > archivesrh:
            oldest = dirs.pop(0)
            try:
                shutil.rmtree(oldest)
            except Exception as e:
                print(f"Error deleting {oldest}: {e}")
        # End Delete

    if method != 'rnt':
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
    return validrlt


def filter_lines_from_list(lines, escaped_user, idx=1):

    regexes = [re.compile(p.replace("{{user}}", escaped_user)) for p in get_exclude_patterns()]
    # filtered = [
    #     line for line in lines
    #     if line and len(line) > idx and line[idx] and not any(r.search(line[idx]) for r in regexes)
    # ]
    filtered = []
    for line in lines:
        if not line or len(line) <= idx:
            continue
        value = line[idx]
        if not value:
            logging.debug("filter_lines_from_list line had no filepath line:%s", line)
            continue

        if not any(r.search(value) for r in regexes):
            filtered.append(line)
    return filtered


# def str_to_bool(x):
#     return str(x).strip().lower() in ("true", "1")
def to_bool(val):
    return val.lower() == "true" if isinstance(val, str) else bool(val)


def multi_value(arg_string):
    return False if isinstance(arg_string, str) and arg_string.strip().lower() == "false" else arg_string


def time_convert(quot, divis, decm):
    tmn = round(quot / divis, decm)
    if quot % divis == 0:
        tmn = quot // divis
    return tmn


# UTC join
def timestamp_from_line(line):
    parts = line.split()
    return " ".join(parts[:2])


def line_included(line, patterns):
    return not any(p in line for p in patterns)
#
# end parsing #


# prev search?
def hsearch(OLDSORT, MODULENAME, argone):

    folders = sorted(glob.glob(f'/tmp/{MODULENAME}_MDY_*'), reverse=True)

    for folder in folders:
        pattern = os.path.join(folder, f"{MODULENAME}xSystemchanges{argone}*")
        matching_files = sorted(glob.glob(pattern), reverse=True)

        for file in matching_files:
            if os.path.isfile(file):
                with open(file, 'r') as f:
                    OLDSORT.clear()
                    OLDSORT.extend(f.readlines())
                break

        if OLDSORT:
            break


# recentchanges
def copy_files(RECENT, RECENTNUL, TMPOPT, argone, THETIME, argtwo, USR, TEMPDIR, archivesrh, autooutput, xzmname, cmode, fmt, lclhome=None):

    # RECENTNUL isnt used holds all filepaths from main search in \0 delimited for file transfers
    # appname = ''
    tmpopt_out = 'tmp_holding'                           # filtered list
    # tout_out = 'toutput.tmp'                                 # tout temp file would hold the \0 delimited file names from RECENTNUL
    sortcomplete_out = 'list_complete_sorted.txt'  # unfiltered used for times only

    if not xzmname:
        xzmname = f"Application{os.getpid()}"

    # if not autooutput and argtwo == "SRC":
    #     while True:
    #         uinpt = input("Press enter for default filename: ").strip()
    #         if uinpt:
    #             appname = uinpt
    #             break
    #         else:
    #             break

    with open('/tmp/' + tmpopt_out, 'w') as f1:  # open('/tmp/' + tout_out, 'wb') as f2:

        for record in TMPOPT:
            if len(record) >= 2:

                date = record[0].strftime(fmt)
                field = record[1]
                f1.write(date + " " + field + '\n')

        # \0 delim filenames
        # f2.write(RECENTNUL)

    # for times only
    with open('/tmp/' + sortcomplete_out, 'w') as f3:
        for record in RECENT:

            date = record[0].strftime(fmt)
            field = record[1]
            f3.write(date + " " + field + '\n')

    if os.path.isfile('/tmp/' + tmpopt_out) and os.path.getsize('/tmp/' + tmpopt_out) > 0:

        script_path = "/usr/local/save-changesnew/recentchanges"
        if lclhome:
            script_path = os.path.join(lclhome, 'recentchanges')
        try:
            script_dir = os.path.dirname(script_path)
            auto_output = str(autooutput).lower()
            proc = subprocess.Popen(
                [
                    script_path,
                    str(argone),
                    str(THETIME),
                    str(argtwo),
                    USR,
                    xzmname,
                    TEMPDIR,
                    tmpopt_out,
                    sortcomplete_out,
                    str(archivesrh),
                    cmode,
                    auto_output
                ],
                cwd=script_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            all_output = []
            last_line = ""

            stdout = proc.stdout
            if stdout is None:
                raise RuntimeError("stdout is None")

            try:
                for line in stdout:

                    print(last_line)
                    all_output.append(line)
                    last_line = line.strip()
                    if "Filename or Selection" in line:
                        uinpt = input().strip()
                        if uinpt:
                            if proc.stdin is not None:
                                proc.stdin.write(uinpt + '\n')
                                proc.stdin.flush()

            except KeyboardInterrupt:
                proc.terminate()

            proc.wait()
            return_code = proc.returncode

            output = ''.join(all_output)

            if return_code != 0:
                print(f'/rntfiles.xzm failed unable to make xzm. errcode:{return_code}')
                print("ERROR:", output)
                return

            if "Your module has been created." in output:
                result = "xzm"
            else:
                result = last_line

            if "prev" not in last_line and "nofiles" not in last_line:
                print(last_line)

            return result
        except Exception as e:
            msg = f"Error copying files for recentchanges script {script_path} error: {e} {type(e).__name__}"
            print(msg)
            logging.error(msg, exc_info=True)


def postop(all_data, USRDIR, toml, lclhome=None):

    log = '/tmp/log.log'

    with open(log, 'w', encoding="utf-8") as file2:
        for entry in all_data:
            fixed_fields = " ".join(str(field) for field in entry[:-1])
            line = f"{fixed_fields} {entry[-1]}"
            file2.write(line + "\n")

    script_file = "postop.sh"
    script_path = "/usr/local/save-changesnew/" + script_file
    if lclhome:
        script_path = os.path.join(lclhome, script_file)
    cmd = [
        script_path,
        log,
        USRDIR,
        str(toml)
    ]
    script_dir = os.path.dirname(script_path)
    result = subprocess.run(cmd, cwd=script_dir, capture_output=True, text=True)
    print(result.stdout)

    if result.returncode == 1:
        print("Post op failed")
        return 1


def run_doctrine(appdata_local, USRDIR, SORTCOMPLETE, TMPOPT, logf, rout, toml_file, escaped_user, method, fmt):

    if method != "rnt":
        if logf is TMPOPT:
            SORTCOMPLETE = filter_lines_from_list(SORTCOMPLETE, escaped_user)

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

        if len(record) < 17:
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
        lastmodified = record[13] if record[13] else "None None"    # 12 13
        is_copy = "y" if record[16] in copy_paths else "None"       # 14
        file_path = record[16]                                      # 15
        # inode = record[3]
        # checksum = record[5]
        # mode = record[10]
        # hardlink = record[14]
        # usec_zero = record[15]
        all_data.append((mtime, changetime, atime, filesize, sym, user, group, cam, lastmodified, is_copy, file_path))

    postop(all_data, USRDIR, toml_file, appdata_local)
