# developer buddy v5.0 core                     original 09/26/2025 updated 01/13/2026
import csv
import getpass
import glob
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import datetime
from io import StringIO
from pathlib import Path
from filter import get_exclude_patterns
from fsearch import process_find_lines
from fsearchfnts import upt_cache
from pyfunctions import cprint
from pyfunctions import epoch_to_date
from pyfunctions import parse_datetime
from pyfunctions import sbwr
from pyfunctions import unescf_py


# Note: For database cacheclear / terminal supression see pyfunctions.py


# Globals
QUOTED_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


# inclusions from this script
def get_runtime_exclude_list(USRDIR, log_path, MODULENAME, flth, dbtarget, CACHE_F):

    usrd = os.path.join(USRDIR, f'{MODULENAME}x')

    return [
        flth,
        usrd,
        str(log_path),
        dbtarget,
        CACHE_F
    ]


# Initialize
def intst(target_file, compLVL):
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


# term output
def logic(syschg, nodiff, diffrlt, validrlt, MODULENAME, THETIME, argone, argf, filename, flsrh, method):

    if method == "rnt":
        if validrlt == "prev":
            print("Refer to /rntfiles_MDY folder for the previous search")
        elif validrlt == "nofiles":
            cprint.cyan('There were no files to grab.')
            print()

        if THETIME != "noarguser" and syschg:
            cprint.cyan(f'All system files in the last {argone} seconds are included')

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

    if not syschg:
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

    if os.path.isfile(filepath) and os.path.getsize(filepath) != 0:
        try:
            subprocess.Popen(["sudo", "-u", "guest", dspPATH, filepath])  # , shell=True windows **
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


def is_excluded(webb, file_line):
    return any(re.search(pat, file_line) for pat in webb)


def is_supressed(webb, file_line, flg, supbrwr, supress):
    if flg or supress:
        return True
    if supbrwr and webb:
        return is_excluded(webb, file_line)
    return False


# scr / cerr logic
def filter_output(filepath, escaped_user, filtername, critical, pricolor, seccolor, typ, supbrwr=True, supress=False):
    webb = sbwr(escaped_user)
    flg = False
    with open(filepath, 'r') as f:
        for file_line in f:

            file_line = file_line.strip()
            if file_line.startswith(filtername):

                if not is_supressed(webb, file_line, flg, supbrwr, supress):
                    getattr(cprint, pricolor, lambda msg: print(msg))(f"{file_line} {typ}")
            else:
                if critical != "no":
                    if file_line.startswith(critical) or file_line.startswith("COLLISION"):
                        getattr(cprint, seccolor, lambda msg: print(msg))(f'{file_line} {typ} Critical')
                        flg = True
                else:
                    if not is_supressed(webb, file_line, flg, supbrwr, supress):
                        getattr(cprint, seccolor, lambda msg: print(msg))(f"{file_line} {typ}")
    return flg


# Toml
# update the toml to disable\enable
def update_toml_setting(keyName, settingName, newValue, filePath):

    def format_toml_value(value):
        if isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, str):
            return f'"{value}"'
        elif value is None:
            return '""'
        elif isinstance(value, list):
            # Format as TOML array
            items = []
            for item in value:
                if isinstance(item, str):
                    items.append(f'"{item}"')
                elif isinstance(item, bool):
                    items.append(str(item).lower())
                else:
                    items.append(str(item))
            return "[" + ", ".join(items) + "]"
        else:
            return str(value)

    try:

        fnd = False

        with open(filePath, "r") as f:
            lines = f.readlines()

        with open(filePath, "w") as f:
            for line in lines:
                stripped = line.strip()
                if not fnd and stripped.startswith(f"{settingName}"):
                    fnd = True

                    value_str = format_toml_value(newValue)

                    if "#" in line:
                        _, comment = line.split("#", 1)
                        comment = " #" + comment.rstrip("\n")
                    else:
                        comment = ""

                    f.write(f"{settingName} = {value_str}{comment}\n")
                else:
                    f.write(line)

    except Exception as e:
        print(f"Failed to update toml {filePath} setting. check key value pair {type(e).__name__} {e}")
        raise


def update_config(config_file, setting_name, old_value, quiet=False, lclhome=None):

    script_file = "updateconfig.sh"
    script_path = "/usr/local/save-changesnew/" + script_file
    if lclhome:
        script_path = os.path.join(lclhome, script_file)
    cmd = [
        script_path,
        str(config_file),
        setting_name,
        old_value
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        if not quiet:
            print(result)
    else:
        print(result)
        print(f'Bash script failed {script_path}. error code: {result.returncode}')

# end Toml


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
def find_files(find_command, search_paths, mMODE, file_type, RECENT, COMPLETE, RECENTNUL, init, checksum, updatehlinks, cfr, FEEDBACK, search_start_dt, logging_values, end, cstart):

    table = "logs"
    try:

        if search_paths:
            print(search_paths)
        else:
            print('Running command:', ' '.join(find_command))
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

    file_entries = [entry.decode(errors='backslashreplace') for entry in output.split(b'\0') if entry]
    if file_type == "mtime":
        end = time.time()

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
            if file_type == "mtime":
                file_path = fields[10]
                RECENTNUL += (file_path.encode() + b'\0')  # copy file list `recentchanges` null byte
                if FEEDBACK:  # scrolling terminal look       alternative output
                    print(fields[10])

            # escaped_entry = " ".join(fields)
            records.append(fields)

    if init and checksum:
        cstart = time.time()
        cprint.cyan("Running checksum")

    if file_type == "mtime":
        RECENT, COMPLETE = process_find_lines(records, mMODE, checksum, updatehlinks, "main", table, search_start_dt, 'FSEARCH', logging_values, cfr)
    elif file_type == "ctime":
        RECENT, COMPLETE = process_find_lines(records, mMODE, checksum, updatehlinks, "ctime", table, search_start_dt, 'FSEARCH', logging_values, cfr)
    else:
        raise ValueError(f"Unknown file type: {file_type}")

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
    regexes = [re.compile(p.replace("{user}", escaped_user)) for p in get_exclude_patterns()]
    filtered = [
        line for line in lines
        if line and len(line) > idx and not any(r.search(line[idx]) for r in regexes)
    ]
    return filtered


# def str_to_bool(x):
#     return str(x).strip().lower() in ("true", "1")
def to_bool(val):
    return val.lower() == "true" if isinstance(val, str) else bool(val)


def multi_value(arg_string):
    return False if isinstance(arg_string, str) and arg_string.strip().lower() == "false" else arg_string


def convertn(quot, divis, decm):
    tmn = round(quot / divis, decm)
    if quot % divis == 0:
        tmn = quot // divis
    return tmn


# return filenm
def getnm(locale, ext=''):
    f_name = os.path.basename(locale)
    root, _ = os.path.splitext(f_name)
    return root + ext


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


def changeperm(path, uid, gid=0, mode=0o644):
    try:
        os.chown(path, uid, gid)
        os.chmod(path, mode)
    except FileNotFoundError:
        print(f"File not found: {path}")
    except Exception as e:
        print(f"chown error {path}: {e}")


def get_usr():
    try:
        return getpass.getuser()
    except OSError:
        print("unable to get username, using fallback")
        # fallback to last folder in home path
        return Path.home().parts[-1]


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


def check_for_gpg():
    try:
        gpg_path = shutil.which("gpg")
        gnupg_home = os.getenv("GNUPGHOME")

        result = subprocess.run(
            ["gpg", "--list-secret-keys"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return gpg_path, gnupg_home
        # if result.returncode == 0 and not result.stdout.strip():
        #     subprocess.run(
        #         ["gpgconf", "--kill", "gpg-agent"],
        #         check=False,
        #     )
    except FileNotFoundError as e:
        print(f"[ERROR] check_for_gpg gpg not found {e}")
    except Exception as e:
        print(f"check_for_gpg {type(e).__name__} {e} \n {traceback.format_exc()}")
    return None, None


def iskey(email):
    try:
        result = subprocess.run(
            ["gpg", "--list-secret-keys"],
            capture_output=True,
            text=True,
            check=True
        )
        return (email in result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error running gpg:", e)
    return False


def genkey(email, name, TEMPD, passphrase=None):

    if not passphrase:
        p = getpass.getpass("Enter passphrase for new GPG key: ")
    else:
        p = passphrase
    params = f"""%echo Generating a GPG key
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: {name}
Name-Email: {email}
Expire-Date: 0
Passphrase: {p}
%commit
%echo done
"""
    with tempfile.TemporaryDirectory(dir=TEMPD) as kp:

        ftarget = os.path.join(kp, 'keyparams.conf')
        try:

            with open(ftarget, "w", encoding="utf-8") as f:
                f.write(params)
            os.chmod(ftarget, 0o600)

            cmd = [
                "gpg",
                "--batch",
                "--pinentry-mode", "loopback",
                "--passphrase", p,
                "--generate-key"
            ]
            # subprocess.run(cmd, check=True)
            # Open the params file and pass it as stdin
            with open(ftarget, "rb") as param_file:
                subprocess.run(cmd, check=True, stdin=param_file)
            print(f"GPG key generated for {email}.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to generate GPG key: {e} \n {traceback.format_exc()}")
        except Exception as e:
            print(f'Unable to make GPG key: {type(e).__name__} {e} {traceback.format_exc()}')
        finally:
            removefile(ftarget)
    return False


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


# enc mem
def encrm(c_data: str, opt: str, r_email: str, no_compression: bool = True, armor: bool = False) -> bool:
    try:
        cmd = [
            "gpg",
            "--batch",
            "--yes",
            "--encrypt",
            "-r", r_email,
            "-o", opt
        ]

        if no_compression:
            cmd.extend(["--compress-level", "0"])

        if armor:
            cmd.append("--armor")

        subprocess.run(
            cmd,
            input=c_data.encode("utf-8"),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True

    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode().strip() if e.stderr else str(e)
        print(f"[ERROR] Cache Encryption failed: {err_msg}")
    return False


# dec mem
def decrm(src):

    try:
        cmd = [
            "gpg",
            "--quiet",
            "--batch",
            "--yes",
            "--decrypt",
            src
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")  # check=True removed for parsing errors
        if result.returncode != 0:
            if result.returncode == 2:
                stderr = (result.stderr or "").lower()
                if "permission" not in stderr and "pinentry" not in stderr:
                    # No key
                    return None
            raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
        return result.stdout

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Cache Decryption failed: {e} {type(e).__name__} \n {traceback.format_exc()}")
        combined = "\n".join(filter(None, [e.stdout, e.stderr]))
        if combined:
            print(combined)
        if "permission" in (e.stderr or "").lower():
            print("Invalid password or Pinentry problem ensure using the correct pinentry package 15.0 or current. current for porteus alpha")
            print("Alternatively try to use pinentry-gtk-2 so root can prompt for password**")
        return False


def encr(database, opt, email, no_compression, dcr=False):
    try:
        cmd = [
                "gpg",
                "--yes",
                "--encrypt",
                "-r", email,
                "-o", opt,
        ]
        if no_compression:
            cmd.extend(["--compress-level", "0"])
        cmd.append(database)
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        if not dcr:
            removefile(database)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to encrypt:  {e} return_code: {e.returncode}")
        combined = "\n".join(filter(None, [e.stdout, e.stderr]))
        if combined:
            print("[OUTPUT]\n" + combined)
    except FileNotFoundError as e:
        print("[ERROR] File not found possibly: ", database, " error: ", e)
    except Exception as e:
        print(f"[ERROR] general exc encr: {e} {type(e).__name__} \n {traceback.format_exc()}")
    return False


def decr(src, opt):  # traceback ****
    if os.path.isfile(src):
        try:
            cmd = [
                "gpg",
                "--yes",
                "--decrypt",
                "-o", opt,
                src
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)  # check=True

            if result.returncode != 0:
                if result.returncode == 2:
                    if "pinentry" not in (result.stderr or "").lower():
                        # No key
                        return None
                raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
            return True

        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Decryption failed:  {e} return_code: {e.returncode}")
            combined = "\n".join(filter(None, [e.stdout, e.stderr]))
            if combined:
                print("[OUTPUT]\n" + combined)

        except FileNotFoundError as e:
            print("GPG not found. Please ensure GPG is installed. or could not find file: ", src, " error: ", e)
        except Exception as e:
            print(f"[ERROR] decr Unexpected exception err: {e} {type(e).__name__} \n {traceback.format_exc()}")
    else:
        print(f"[ERROR] File {src} not found. Ensure the .gpg file exists.")

    return False


def decr_ctime(CACHE_F):
    if not CACHE_F or not os.path.isfile(CACHE_F):
        return {}

    csv_path = decrm(CACHE_F)
    if not csv_path:
        if csv_path is None:
            print("Root doesnt have the key.")
            print("if having problems run recentchanges query to try to repair key pair or delete the file.")
        print(f"Unable to retrieve cache file {CACHE_F} quitting.")
        sys.exit(1)

    cfr_src = {}
    reader = csv.DictReader(StringIO(csv_path), delimiter='|')

    for row in reader:
        root = row.get('root')
        if not root:
            continue

        # normalize types
        try:
            size = int(row['size']) if row.get('size') else None
        except ValueError:
            size = None
        try:
            modified_ep = float(row['modified_ep']) if row.get('modified_ep') else None
        except ValueError:
            modified_ep = None

        cfr_src.setdefault(root, {})[modified_ep] = {
            "checksum": row.get('checksum', None),
            "size": size,
            "modified_time": row.get('modified_time', None),
            "owner": row.get('owner', None),
            "domain": row.get('domain', None)
        }

    return cfr_src


# xRC functions

def process_status(pattern):
    try:
        result = subprocess.run(
            ["pgrep", "-af", pattern],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception as e:
        logging.error(f"process_status xRC failed to check if process was running: {e} {type(e).__name__}", exc_info=True)
    return False


def _fk_process(pattern):
    try:
        result = subprocess.run(
            ["pkill", "-f", pattern],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception as e:
        logging.error(f"_fk_process xRC failure to close process. err: {e} {type(e).__name__} \n", exc_info=True)
    return False


def strup(inotify_creation_file, CACHE_F, checksum, updatehlinks, MODULENAME, log_file, lclhome=None):
    script_path = "/usr/local/save-changesnew/start_inotify"
    if lclhome:
        script_path = os.path.join(lclhome, 'start_inotify')
    cmd = [
        script_path,
        str(inotify_creation_file),
        MODULENAME,
        str(CACHE_F),
        str(checksum).lower(),
        str(updatehlinks).lower(),
        "ctime",
        "3600"
    ]
    try:
        script_dir = os.path.dirname(script_path)
        subprocess.run(cmd, cwd=script_dir, capture_output=True, text=True, check=True)
        logging.debug("strup completed successfully")
    except subprocess.CalledProcessError as e:
        print("xRC unable to start inotify logged to", log_file)
        logging.error(f"error in strup: {e} {type(e).__name__}", exc_info=True)
        combined = "\n".join(filter(None, [e.stdout, e.stderr]))
        if combined:
            logging.error("[OUTPUT]\n" + combined)
    except Exception as e:
        print("xRC logged an exception to", log_file)
        logging.error(f"strup General exception unable to start inotify wait: {e} {type(e).__name__}", exc_info=True)


def parse_line(line):
    quoted_match = QUOTED_RE.search(line)
    if not quoted_match:
        return None
    raw_filepath = quoted_match.group(1)

    # filepath = ap_decode(raw_filepath)  # from bash / bash python
    filepath = raw_filepath  # escaped but decoded in parselog

    line_without_file = line.replace(quoted_match.group(0), '').strip()  # Remove quoted path
    other_fields = line_without_file.split()

    if len(other_fields) < 7:
        return None

    timestamp1_subfld1 = None if other_fields[0] in ("", "None") else other_fields[0]
    timestamp1_subfld2 = None if other_fields[1] in ("", "None") else other_fields[1]
    timestamp1 = None if not timestamp1_subfld1 or not timestamp1_subfld2 else f"{timestamp1_subfld1} {timestamp1_subfld2}"
    if timestamp1:
        timestamp1 = parse_datetime(timestamp1)
    if not timestamp1:
        return None

    timestamp2_subfld1 = None if other_fields[2] in ("", "None") else other_fields[2]
    timestamp2_subfld2 = None if other_fields[3] in ("", "None") else other_fields[3]
    timestamp2 = None if not timestamp2_subfld1 or not timestamp2_subfld2 else f"{timestamp2_subfld1} {timestamp2_subfld2}"

    inode = other_fields[4]

    timestamp3_subfld1 = None if other_fields[5] in ("", "None") else other_fields[5]
    timestamp3_subfld2 = None if other_fields[6] in ("", "None") else other_fields[6]
    timestamp3 = None if not timestamp3_subfld1 or not timestamp3_subfld2 else f"{timestamp3_subfld1} {timestamp3_subfld2}"

    rest = other_fields[7:]

    return [timestamp1, filepath, timestamp2, inode, timestamp3] + rest


def parselog(file, table, checksum):

    results = []

    for line in file:
        try:
            inputln = parse_line(line)
            if not inputln or not inputln[1].strip():
                logging.debug("parselog missing line or filename from input , table: %s. skipping.. record: %s", table, line)
                continue

            n = len(inputln)
            if table == 'sortcomplete' or table == 'tout':
                if checksum:
                    if n < 15:
                        print("parselog checksum, input out of boundaries skipping")
                        logging.debug("table: %s record length less than required 15. skipping.. record: %s", table, line)
                        continue
                else:
                    if n < 10:
                        print("parselog no checksum, input out of boundaries skipping")
                        logging.debug("table %s record length less than required 10. skipping.. record: %s", table, line)
                        continue

            timestamp = inputln[0]
            filename = unescf_py(inputln[1])
            escf_path = inputln[1]
            changetime = inputln[2]
            inode = None if inputln[3] in ("", "None") else inputln[3]
            accesstime = inputln[4]
            checks = None if n > 5 and inputln[5] in ("", "None") else (inputln[5] if n > 5 else None)
            filesize = None if n > 6 and inputln[6] in ("", "None") else (inputln[6] if n > 6 else None)
            sym = None if n <= 7 or inputln[7] in ("", "None") else inputln[7]
            onr = None if n <= 8 or inputln[8] in ("", "None") else inputln[8]
            gpp = None if n <= 9 or inputln[9] in ("", "None") else inputln[9]
            pmr = None if n <= 10 or inputln[10] in ("", "None") else inputln[10]
            cam = None if n <= 11 or inputln[11] in ("", "None") else inputln[11]
            timestamp1 = None if n <= 12 or inputln[12] in ("", "None") else inputln[12]
            timestamp2 = None if n <= 13 or inputln[13] in ("", "None") else inputln[13]
            lastmodified = None if not timestamp1 or not timestamp2 else f"{timestamp1} {timestamp2}"
            usec = None if n <= 14 or inputln[14] in ("", "None") else inputln[14]
            hardlink_count = None if n <= 15 or inputln[15] in ("", "None") else inputln[15]

            if table == 'sys':
                count = 0
                results.append((timestamp, filename, changetime, inode, accesstime, checks, filesize, sym, onr, gpp, pmr, cam, lastmodified, count))
            elif table == 'sortcomplete' or table == 'tout':

                if not checksum:
                    cam = checks
                    timestamp1 = filesize
                    timestamp2 = sym
                    lastmodified = None if not timestamp1 or not timestamp2 else f"{timestamp1} {timestamp2}"
                    usec = onr
                    hardlink_count = gpp
                    checks = filesize = sym = onr = gpp = None

                results.append((timestamp, filename, changetime, inode, accesstime, checks, filesize, sym, onr, gpp, pmr, cam, lastmodified, hardlink_count, escf_path, usec))
            else:
                raise ValueError("Supplied table not in accepted boundaries: sys or sortcomplete. value supplied", table)
        except Exception as e:
            print(f'Problem detected in parser parselog for line {line} err: {type(e).__name__}: {e} \n skipping..')
            logging.error("General error parselog , table %s  line: %s \n error: %s", table, line, type(e).__name__, exc_info=True)

    return results


def rotate_cache(cfr, CACHE_F):
    if CACHE_F.is_file():
        rotated = CACHE_F.with_name(CACHE_F.name + ".old")
        if rotated.exists():
            logging.debug("init_recentchanges old cachefile already existed %s", rotated)
            removefile(rotated)
        os.rename(CACHE_F, rotated)
        with rotated.open("r") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    logging.debug("Skipping possibly empty line from cache file: %s", line)
                    continue
                try:
                    metadata, checksum, filepath = line.split("\t", maxsplit=2)
                    filepath = filepath.strip()
                    if not filepath:
                        logging.debug("Skipping malformed line in cache file with empty filepath: %s", line)
                        continue
                except ValueError:
                    print("Skipping malformed line in cache file")
                    logging.error("Failed to parse delimiter in cache file line: %s", line)
                    continue
                try:
                    _, size, mtime_epoch = metadata.split("|")  # inode not used
                    size = int(size)
                    mtime_epoch = float(mtime_epoch)
                except ValueError:
                    print(f"Skipping malformed metadata in cache file: {metadata}")
                    logging.error("Failed to parse metadata in cache file line: %s", line)
                    continue

                time_stamp_frm = epoch_to_date(mtime_epoch)  # is_valid_datetime
                if time_stamp_frm:
                    time_stamp = time_stamp_frm.replace(microsecond=0)
                    logging.debug("Inserting %s %s %s %s %s", checksum, size, time_stamp, mtime_epoch, filepath)
                    upt_cache(cfr, checksum, size, time_stamp, mtime_epoch, filepath)
                else:
                    print("xRC invalid time_stamp or format detected in cache file.")
                    logging.debug("xRC Invalid timestamp in cache file line: %s", line)
        removefile(rotated)


def parse_tout(log_file, checksum):
    tout_files = []
    all_files = []

    rotated = log_file.with_name(log_file.name + ".old")
    if os.path.exists(rotated):
        logging.debug("init_recentchanges old tout already existed %s", rotated)
        removefile(rotated)
    os.rename(log_file, rotated)

    with rotated.open('r') as f:
        tout_files = f.readlines()

    if tout_files:
        all_files = parselog(tout_files, 'sortcomplete', checksum)

    removefile(rotated)
    return all_files


def init_recentchanges(lclhome, inotify_creation_file, cfr, xRC, checksum, updatehlinks, MODULENAME, log_file=None):
    try:
        all_files = []
        search_pattern = os.path.join(lclhome.name, "inotify")

        if checksum and xRC:

            cached = Path("/tmp/dbctimecache/")

            CACHE_F = cached / "ctimecache"

            os.makedirs(cached, mode=0o700, exist_ok=True)
            # os.chown(cached, uid, gid)
            # if os.path.isdir(cached):
            #     os.chmod(cached, 0o700)

            if process_status(search_pattern):
                _fk_process('inotifywait -m -r -e create -e moved_to --format %e|%w%f%0')

                rotate_cache(cfr, CACHE_F)

                if os.path.isfile(inotify_creation_file):

                    all_files = parse_tout(inotify_creation_file, checksum)

                open(inotify_creation_file, 'w').close()
                if not process_status(search_pattern):
                    strup(inotify_creation_file, CACHE_F, checksum, updatehlinks, MODULENAME, log_file, lclhome)
                else:
                    removefile(inotify_creation_file)
            else:
                removefile(inotify_creation_file)
                strup(inotify_creation_file,  CACHE_F, checksum, updatehlinks, MODULENAME, log_file, lclhome)
        else:
            if process_status(search_pattern):
                _fk_process('inotifywait -m -r -e create -e moved_to --format %e|%w%f%0')
                removefile(inotify_creation_file)
        return all_files
    except Exception as e:
        logging.error(f"Error in xRC error: {e} {type(e).__name__}", exc_info=True)
    return []

# end xRC functions
