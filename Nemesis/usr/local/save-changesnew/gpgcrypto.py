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


def set_cmd(user):
    cmd = []
    if user:
        if user != 'root':
            cmd += ["sudo", "-u", user]
    return cmd


# dec mem
def decrm(src):

    try:
        cmd = ["gpg", "--quiet", "--batch", "--yes", "--decrypt", src]

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


def encr(database, opt, email, no_compression=False, dcr=False):
    try:
        cmd = ["gpg", "--yes", "--encrypt", "-r", email, "-o", opt]
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
            cmd = ["gpg", "--yes", "--decrypt", "-o", opt, src]
            result = subprocess.run(cmd, capture_output=True, text=True)  # check=True

            if result.returncode != 0:
                if result.returncode == 2:
                    stderr = (result.stderr or "").lower()
                    if "permission" not in stderr and "pinentry" not in stderr:
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


def encr_cache(cfr, CACHE_F, user, uid, gid, email, compLVL):
    data_to_write = dict_to_list(cfr)
    ctarget = dict_string(data_to_write)

    nc = cnc(CACHE_F, compLVL)

    new_file = False
    if not os.path.isfile(CACHE_F):
        new_file = True

    rlt = encrm(ctarget, CACHE_F, email, no_compression=nc, armor=False)
    if not rlt:
        print("Reencryption failed cache not saved.")

    if new_file:
        change_perm(CACHE_F, uid, gid)


def decr_ctime(CACHE_F, user):
    if not CACHE_F or not os.path.isfile(CACHE_F):
        return {}

    csv_path = decrm(CACHE_F)
    if not csv_path:
        if csv_path is None:
            print("Root doesnt have the key.")
            print("if having problems run recentchanges reset to clear .gpg files and keys")
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
            sys.exit(1)
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
