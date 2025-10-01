# 09/26/2025           developer buddy core
import getpass
import glob
import os
import re
import subprocess
import tempfile
import tomllib
from filter import get_exclude_patterns
from pyfunctions import cprint
from pyfunctions import sbwr

# see pyfunctions for cacheclear/supression
# toml
def load_config(confdir):
    with open(confdir, 'rb') as f:
        config = tomllib.load(f)
    return config

# term output
def logic(syschg, nodiff, diffrlt, validrlt, MODULENAME, THETIME, argone, argf, filename, flsrh, imsg, method):
    
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
def display(dspEDITOR, filepath, syschg):
    if syschg:
        if dspEDITOR == "xed":
            if os.path.isfile("/usr/bin/xed"):
                try:
                    subprocess.run(["xed", filepath], check=True)
                    #subprocess.Popen(["xed", filepath])
                except subprocess.CalledProcessError as e:
                    print(f"Editor exited with an error: {e}")
            else:
                print(f'{dspEDITOR} not installed')
        if dspEDITOR == "featherpad":
            if os.path.isfile("/usr/bin/featherpad"):
                try:
                    subprocess.run(["featherpad", filepath], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Editor exited with an error: {e}")
            else:
                print(f'{dspEDITOR} not installed')


# filter files with filter.py
def filter_lines_from_list(lines, user):
    escaped_user = re.escape(user)
    regexes = [re.compile(p.replace("{user}", escaped_user)) for p in get_exclude_patterns()]
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
def get_runtime_exclude_list(USR, logpst, statpst, dbtarget, CACHE_F):
    return [
        "/usr/local/save-changesnew/flth.csv",
        f"/home/{USR}/Downloads/rnt",
        logpst,
        statpst,
        dbtarget,
        CACHE_F
    ]
# return filenm
def getnm(locale, ext=''):
      root = os.path.basename(locale)
      root, ext = os.path.splitext(root)
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

    folders = sorted(glob.glob(f'/tmp/{MODULENAME}_MDY*'), reverse=True)

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
        os.remove(fpath)

    except Exception as e:
        print(f'Problem removing {fpath}')
    except FileNotFoundError:
        pass

def changeperm(path, uid, gid=0, mode=0o644):
    try:
        os.chown(path, uid, gid)
        os.chmod(path, mode)
    except FileNotFoundError:
        print(f"File not found: {path}")
    except Exception as e:
        print(f"chown error {path}: {e}")


def get_linux_distro():
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
        for target in ("porteus", "artix"):
            if target in distro_id or target in distro_name:
                return True
        return False
    except FileNotFoundError:
        print("The file /etc/os-release was not found.")
    except Exception as e:
        print(f'An error occurred: {e}')
    return False

#`recentchanges`
# 
def copyfiles(RECENT, RECENTNUL, TMPOPT, method, argone, argtwo, USR, TEMPDIR, archivesrh, autooutput, cmode, fmt):

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
                        cmode,
                        str(autooutput)
                    ],
                    capture_output=True,
                    text=True
                )
            
                output = copyres.stdout
                print(output)

                if "Your module" in output:
                    return "xzm"
                elif copyres.returncode == 14: # Success
                    return "prev"
                elif copyres.returncode ==7: # .. same first search
                    return "nofiles"
                elif copyres.returncode != 0:
                    print(f'/rntfiles.xzm failed to unable to make xzm. errcode:{copyres.returncode}')
                    print("STDERR:", copyres.stderr)
                
            except Exception as e:
                print(f"Error in recentchangest: {e}")

def iskey(email, TEMPD):
    try:
        result = subprocess.run(
            ["gpg", "--list-secret-keys"],
            capture_output=True,
            text=True,
            check=True
        )
        if email not in result.stdout:
            if genkey(email, TEMPD):
                return True
        else:
            return True
    except subprocess.CalledProcessError as e:
        print("Error running gpg:", e)
    return False

def genkey(email, TEMPD):
    p = getpass.getpass("Enter passphrase for new GPG key: ")
    params = f"""%echo Generating a GPG key
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: John Doe
Name-Email: {email}
Expire-Date: 0
Passphrase: {p}
%commit
%echo done
"""
    with tempfile.TemporaryDirectory(dir=TEMPD) as kp:
        ftarget = os.path.join(kp, 'keyparams.conf')

        with open(ftarget, "w", encoding="utf-8") as f:
            f.write(params)
        os.chmod(ftarget, 0o600)

        try:
            cmd = [
                "gpg",
                "--batch",
                "--pinentry-mode", "loopback",
                "--passphrase", p,
                "--generate-key"
            ]
            # Open the params file and pass it as stdin
            with open(ftarget, "rb") as param_file:
                subprocess.run(cmd, check=True, stdin=param_file)

            print(f"GPG key generated for {email}.")
            return True
        except subprocess.CalledProcessError as e:
            print("Failed to generate GPG key:", e)
        except Exception as e:
            print(f'Unable to make GPG key: {e}')
    return False

def postop(outf, USRDIR, toml, fmt):
    log='/tmp/log.log'
    with open(log, 'a') as file2:
        for entry in outf:
            tss = entry[0].strftime(fmt)
            fp = entry[1]
            file2.write(f'{tss} {fp}\n')

    result=subprocess.run(["/usr/local/save-changesnew/postop.sh", log, USRDIR, toml],capture_output=True,text=True)
    print(result.stdout)

    if result.returncode == 1:
        print("Post op failed")               
        return 1