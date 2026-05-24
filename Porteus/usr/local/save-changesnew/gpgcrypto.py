import csv
import os
import re
import shutil
import sys
import subprocess
import traceback
from io import StringIO
from typing import Any
from rntchangesfunctions import change_perm
from rntchangesfunctions import cnc
from rntchangesfunctions import removefile


# enc mem
def encrm(c_data: str, opt: str, r_email: str, user=None, no_compression: bool = True, armor: bool = False) -> bool:
    try:
        # user = None  # force root gpg agent
        cmd = set_cmd(user)
        cmd += ["gpg", "--batch", "--yes", "--encrypt", "-r", r_email, "-o", opt]

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


def set_cmd(user):
    cmd = []
    if user:
        if user != 'root':
            cmd += ["sudo", "-u", user]
    return cmd


# dec mem
def decrm(src: str, user=None) -> str | None:
    # user = None
    cmd = set_cmd(user)
    cmd += ["gpg", "--decrypt", src]
    ret = subprocess.run(cmd, stdout=subprocess.PIPE)
    if ret.returncode != 0:
        return None
    return ret.stdout.decode("utf-8")

    # original commented out to not conflict with pinentry
    # try:
    #     cmd = ["gpg", "--quiet", "--batch", "--yes", "--decrypt", src]

    #     result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")  # check=True removed for parsing errors
    #     if result.returncode != 0:
    #         if result.returncode == 2:
    #             stderr = (result.stderr or "").lower()
    #             if "permission" not in stderr and "pinentry" not in stderr:
    #                 # No key
    #                 return None
    #         raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
    #     return result.stdout

    # except subprocess.CalledProcessError as e:
    #     print(f"[ERROR] Cache Decryption failed: {e} {type(e).__name__} \n {traceback.format_exc()}")
    #     combined = "\n".join(filter(None, [e.stdout, e.stderr]))
    #     if combined:
    #         print(combined)
    #     if "permission" in (e.stderr or "").lower():
    #         print("Invalid password or Pinentry problem ensure using the correct pinentry package 15.0 or current. current for porteus alpha")
    #         print("Alternatively try to use pinentry-gtk-2 so root can prompt for password**")
    #     return False


def encr(database, opt, email, user=None, no_compression=False, dcr=False):
    try:
        # user = None
        cmd = set_cmd(user)
        cmd += ["gpg", "--yes", "--encrypt", "-r", email, "-o", opt]
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


def decr(src, opt, user=None):
    if os.path.isfile(src):
        # user = None
        cmd = set_cmd(user)
        cmd += ["gpg", "--yes", "--decrypt", "-o", opt, src]
        result = subprocess.run(cmd)  # capture_output=True, text=True
        return result.returncode == 0
    else:
        print(f"[ERROR] File {src} not found. Ensure the .gpg file exists.")
    return False


def encr_cache(cfr, cache_f, user, uid, gid, email, compLVL):
    data_to_write = dict_to_list(cfr)
    ctarget = dict_string(data_to_write)

    nc = cnc(cache_f, compLVL)

    new_file = False
    if not os.path.isfile(cache_f):
        new_file = True

    rlt = encrm(ctarget, cache_f, email, user=user, no_compression=nc, armor=False)
    if not rlt:
        print("Reencryption failed cache not saved.")
    # else:
    #     change_perm(cache_f, uid, gid)
    if new_file:
        change_perm(cache_f, uid, gid)


def decr_ctime(cache_f, user):
    if not cache_f or not os.path.isfile(cache_f):
        return {}

    csv_path = decrm(cache_f, user)
    if not csv_path:
        if csv_path is None:
            print("if having problems run recentchanges reset to clear .gpg files and keys")
        print(f"Unable to retrieve cache file {cache_f}. cache file might be corrupt removing the file may resolve issue. quitting.")
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
            modified_ep = int(row['modified_ep']) if row.get('modified_ep') else None
        except ValueError:
            modified_ep = None
        if modified_ep is None:
            continue
        cfr_src.setdefault(root, {})[modified_ep] = {
            "checksum": row.get('checksum', None),
            "size": size,
            "modified_time": row.get('modified_time', None),
            "owner": row.get('owner', None),
            "domain": row.get('domain', None)
        }

    return cfr_src


# commandline start the users gpg agent before decrypting the cache file above ***
# also used for processhandler.py to start the gpg agent before QProcess
def start_user_agent(gpg_file, user=None):
    """ Not used as requires an existing .gpg file
          pipes will fail with inappropriate ioctl for device unless using gui pinetry """
    # user = None  # force root gpg agent
    cmd = set_cmd(user)
    cmd += ["gpg", "--decrypt", "--dry-run", gpg_file, "-o", "/dev/null"]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    stderr = result.stderr
    if stderr:
        for line in stderr.splitlines():
            if "no secret key" in line.lower():
                print(line)
                print(f"No key for {gpg_file} delete the file to reset")
                return False
    return result.returncode == 0


def start_gpg_agent(source, email):
    """ prep the gpg agent so root can use users cached gpg password """
    result = subprocess.run(["gpg", "--local-user", email, "--output", "/dev/null", "--sign", source], text=True)
    if result.returncode == 0:
        return True
    if result.stderr:
        for line in result.stderr.split(b'\n'):
            """ print(line.decode('utf-8', errors='ignore')) """
            # if b"ioctl" in line.lower():  # wont show up with loopback
            #     return None
            if email.encode() not in line:
                if b"bad passphrase" in line.lower():
                    """ print(line.decode('utf-8', errors='ignore')) """
                    return False
                """ print(line.decode('utf-8', errors='ignore')) """
        for line in result.stdout.split(b'\n'):
            if b"bad passphrase" in line.lower():
                """ print(line) """
                return False

    return None


# can also delete the key with the subid from fingerprint of the .gpg file
def get_subkey_id(gpg_file):
    result = subprocess.run(
        ["gpg", "--decrypt", "--dry-run", gpg_file],
        capture_output=True,
        text=True,
        stderr=subprocess.STDOUT
    )
    for line in result.stdout.split('\n'):
        if 'encrypted' in line.lower():
            match = re.search(r'ID ([A-F0-9]+)', line)
            if match:
                return match.group(1)

    return None


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


def gpg_can_decrypt(usr, dbtarget):
    # emtpy results
    if not os.path.isfile(dbtarget):
        return True
    if usr != 'root':
        st = os.stat(dbtarget)
        is_owned_by_root = (st.st_uid == 0)
        if is_owned_by_root:
            print(f"{dbtarget} is owned by root. permission must be owned by {usr}. set permission to continue.")
            return False
    return True

    # result = subprocess.run(
    #     ["sudo", "gpg", "--decrypt", "--dry-run", dbtarget],
    #     stdout=subprocess.DEVNULL,
    #     stderr=subprocess.PIPE,
    #     text=True
    # )
    # stderr = result.stderr
    # if result.returncode == 2 and stderr:
    #     for line in stderr.splitlines():
    #         print(line)
    #         line_lower = line.lower()
    #         if "cancelled" in line_lower or "bad passphrase" in line_lower:
    #             return True
    #         if "no secret key" in line_lower:
    #             return False
    # return True


# prepare for file output
def dict_to_list(cachedata: dict[str, dict[Any, dict[str, Any]]]) -> list[dict[str, Any]]:
    data_to_write = []
    for root, versions in cachedata.items():
        for modified_ep, metadata in versions.items():
            row = {
                "checksum": metadata.get("checksum") or '',
                "size": '' if metadata.get("size") is None else metadata["size"],
                "modified_time": '' if metadata.get("modified_time") is None else metadata["modified_time"],
                "modified_ep": '' if modified_ep is None else modified_ep,
                # "user": metadata.get("user"),
                # "group": metadata.get("group"),
                "root": root,
            }
            data_to_write.append(row)
    return data_to_write


# recentchangessearch
def dict_string(data: list[dict]) -> str:
    if not data:
        return ""
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys(), delimiter='|', quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()
