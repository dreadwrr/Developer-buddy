import getpass
import os
import subprocess
import tempfile
import traceback
from typing import Any
from configfunctions import get_user
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


# required for batch deleting keys
def get_key_fingerprint(email, no_key=False):
    cmd = ["gpg", "--list-keys", "--with-colons", email]
    if no_key:
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


def delete_gpg_keys(usr, email, dbtarget, ctimecache):

    def exec_delete_keys(usr, current_usr, email, fingerprint):
        silent: dict[str, Any] = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}

        if usr == 'root':
            subprocess.run(["gpg", "--batch", "--yes", "--delete-secret-keys", fingerprint], **silent)
            subprocess.run(["gpg", "--batch", "--yes", "--delete-keys", fingerprint], **silent)
        else:
            subprocess.run(["gpg", "--batch", "--yes", "--delete-secret-keys", fingerprint], **silent)
            subprocess.run(["gpg", "--batch", "--yes", "--delete-keys", fingerprint], **silent)
            if current_usr == 'root':
                subprocess.run(["sudo", "-u", usr, "gpg", "--batch", "--yes", "--delete-secret-keys", fingerprint], **silent)
                subprocess.run(["sudo", "-u", usr, "gpg", "--batch", "--yes", "--delete-keys", fingerprint], **silent)
            else:
                subprocess.run(["sudo", "gpg", "--batch", "--yes", "--delete-secret-keys", fingerprint], **silent)
                subprocess.run(["sudo", "gpg", "--batch", "--yes", "--delete-keys", fingerprint], **silent)
        print("Keys cleared for", email, " fingerprint: ", fingerprint)

    while True:

        uinp = input(f"Warning recent.gpg will be cleared. Reset\\delete gpg keys for {email} (Y/N): ").strip().lower()
        if uinp == 'y':
            confirm = input("Are you sure? (Y/N): ").strip().lower()
            if confirm == 'y':

                result = False

                current_usr = get_user()

                # look in root for key
                fingerprint = get_key_fingerprint(email, no_key=True)
                if fingerprint:
                    result = True
                    # delete for user and root
                    exec_delete_keys(usr, current_usr, email, fingerprint)

                # look for key in user
                fingerprint = get_key_fingerprint(email, no_key=False)
                if fingerprint:
                    result = True
                    exec_delete_keys(usr, current_usr, email, fingerprint)

                removefile(ctimecache)
                removefile(dbtarget)

                if result:

                    # print(f"\nDelete {dbtarget} if it exists as it uses the old key pair.")
                    return 1
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
            return 0
        else:
            print("Invalid input, please enter 'Y' or 'N'.")


def reset_gpg_keys(usr, email, dbtarget, ctimecache, agnostic_check, no_key=False):
    if agnostic_check is False and no_key is True:
        print("only root has key\n")
    elif agnostic_check is True and no_key is False:
        print("only user has key. Select n and manually import the key for root to fix it. or delete the key pair to reset state.\n")
    print("A problem was detected with key pair. ")
    return delete_gpg_keys(usr, email, dbtarget, ctimecache)
