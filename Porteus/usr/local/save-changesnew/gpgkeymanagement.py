import getpass
import os
import subprocess
import tempfile
import traceback
from pathlib import Path
from typing import Any
from rntchangesfunctions import removefile


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


def genkey(user, email, name, dbtarget, CACHE_F, TEMPD, passphrase=None):

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
                "--passphrase-fd", "0",
                "--generate-key",
                ftarget
            ]
            subprocess.run(
                cmd,
                input=(p + "\n").encode(),
                check=True
            )
            # Open the params file and pass it as stdin
            # with open(ftarget, "rb") as param_file:
            #     subprocess.run(
            #         cmd, check=True, stdin=param_file)
            clear_gpg(user, dbtarget, CACHE_F)
            print(f"GPG key generated for {email}.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to generate GPG key: {e}")
            if e.stderr:
                print(e.stderr.decode(errors="replace"))
        except Exception as e:
            print(f'Unable to make GPG key: {type(e).__name__} {e} {traceback.format_exc()}')
        finally:
            removefile(ftarget)
        return False


# required for batch deleting keys
def get_key_fingerprint(email, root_target=None):
    cmd = ["gpg", "--list-keys", "--with-colons", email]
    if root_target:
        cmd = ["sudo"] + cmd
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    for line in result.stdout.split('\n'):
        if line.startswith('fpr:'):
            return line.split(':')[9]
    return None


def remove_gpg_keys(args):
    if len(args) < 5:
        print("Incorrect usage. reset <USR> <email> <app_install>")
        return 1
    user = args[2]
    email = args[3]
    appdata_local = Path(args[4])
    dbtarget = appdata_local / "recent.gpg"
    ctimecache = appdata_local / "ctimecache.gpg"
    return delete_gpg_keys(user, email, dbtarget, ctimecache)


def clear_gpg(usr, dbtarget, CACHE_F):
    """ delete ctimecache & db .gpg """
    for r in (CACHE_F, dbtarget):
        p = Path(r)
        try:
            is_root_owned = p.exists() and p.stat().st_uid == 0
            cmd = (["sudo"] if usr != "root" and is_root_owned else []) + ["/bin/rm", "-f", str(p)]
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error clearing {p}: {e}")
        except FileNotFoundError:
            pass


def delete_gpg_keys(usr, email, dbtarget, ctimecache):

    def exec_delete_keys(usr, email, fingerprint):
        silent: dict[str, Any] = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}

        if usr == 'root':
            subprocess.run(["gpg", "--batch", "--yes", "--delete-secret-keys", fingerprint], **silent)
            subprocess.run(["gpg", "--batch", "--yes", "--delete-keys", fingerprint], **silent)
        else:
            subprocess.run(["gpg", "--batch", "--yes", "--delete-secret-keys", fingerprint], **silent)
            subprocess.run(["gpg", "--batch", "--yes", "--delete-keys", fingerprint], **silent)
            subprocess.run(["sudo", "gpg", "--batch", "--yes", "--delete-secret-keys", fingerprint], **silent)
            subprocess.run(["sudo", "gpg", "--batch", "--yes", "--delete-keys", fingerprint], **silent)

        print("Keys cleared for", email, " fingerprint: ", fingerprint)

    while True:

        uinp = input(f"Warning recent.gpg will be cleared. Reset\\delete gpg keys for {email} (Y/N): ").strip().lower()
        if uinp == 'y':
            confirm = input("Are you sure? (Y/N): ").strip().lower()
            if confirm == 'y':

                result = False

                # look for key in user and or root
                fingerprint = get_key_fingerprint(email)
                if fingerprint:
                    result = True
                    exec_delete_keys(usr, email, fingerprint)

                # look for key in user
                if usr != "root":
                    fingerprint = get_key_fingerprint(email, root_target=True)
                    if fingerprint:
                        result = True
                        exec_delete_keys(usr, email, fingerprint)

                clear_gpg(usr, dbtarget, ctimecache)

                if result:

                    # print(f"\nDelete {dbtarget} if it exists as it uses the old key pair.")
                    return 0
                else:
                    print(f"No key found for {email}")
                    return 2

            else:
                uinp = 'n'

        if uinp == 'n':
            print("To import the key for one to the other to attempt to repair it, try the following. If it doesn't work delete the key pair and start over.")
            print("\nAs user or root:")
            print(f"gpg --batch --yes --pinentry-mode loopback --export-secret-keys --armor {email} > key.asc")
            print("user or root")
            print("gpg --batch --yes --pinentry-mode loopback --import key.asc")
            print("shred -u key.asc")
            print(f"gpg --edit-key {email}")
            print("trust")
            print("5")
            print("y")
            print("quit")
            return 1
        else:
            print("Invalid input, please enter 'Y' or 'N'.")


def reset_gpg_keys(usr, email, dbtarget, ctimecache, agnostic_check, no_key=False):
    if agnostic_check is False and no_key is True:
        print("only root has key\n")
    elif agnostic_check is True and no_key is False:
        print("only user has key. Select n and manually import the key for root to fix it. or delete the key pair to reset state.\n")
    print("A problem was detected with key pair. ")
    return delete_gpg_keys(usr, email, dbtarget, ctimecache)
