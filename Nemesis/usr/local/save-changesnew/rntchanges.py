#!/usr/bin/env python3
# v5.0                                                       06/21/2026
# This script is the entry point for recentchanges. The inv flag is passed in from from /usr/local/recentchanges/filteredsearch script from /usr/local/bin/rnt symlink
#
# There are 2 positional arguments. a third is the inv flag
# the filtered arg just changes a regular search to the inverse for recentchanges search, recentchanges search n, recentchanges search myfile
#
# for recentchanges the arguments shift. as its recentchanges or recentchanges n. There is a SRC tag which will make a .xzm
# from a root directory with the most recent files.
#
# the main purpose is to output unfiltered system files and tmp files. 
#
# recentchanges - output to /tmp
# can take 1 argument the time n or no arguments for 5 minutes. 
# as well as the SRC tag recentchanges SRC 60, recentchanges 60 SRC or recentchanges SRC
#
# recentchanges search - output to Downloads 
# can take 1 argument the time n or no arguments for 5 minutes. 
# as well as newer than file with recentchanges search myfile or recentchanges search /home/guest/myfile. it is filtered rather than unfiltered and if called from rnt symlink its unfiltered
# .
# recentchanges query - show stats from the database from past searches
#
# recentchanges reset - delete gpg key and gpg files and prompt to reset config files
#
# argone - the search time for `recentchanges` or the keyword search for `recentchanges search` or keyword query to get stats from database
# argtwo - search time for `recentchanges search`
# argf - inv flag from rnt symlink
# flake8: noqa: E402
import sys
from gpgkeymanagement import remove_gpg_keys
from recentchangessearch import main as recentchanges_main


def main(argv):

    max_len = 7
    len_arg = len(argv)
    if len_arg > max_len:
        print("Incorrect usage. max from rnt 6. provided: ", len(argv))
        print("Required <usr> <pwd>")
        print("please call from /opt/recentchanges/recentchanges")
        return 1
    if len_arg < 3:
        print("Incorrect usage. <usr> <pwd> please call from /opt/recentchanges/recentchanges")
        return 1
    if argv[1] == "reset":
        # return query_main(usr, True)
        return remove_gpg_keys(argv)

    usr = argv[1]  # usr = os.getenv("USR")
    pwd = argv[2]

    argone = argv[3] if len(sys.argv) > 3 and argv[3] else "noarguser"
    argtwo = argv[4] if len(sys.argv) > 4 and argv[4] else "noarguser"

    srcDIR = ""
    method = ""
    argf = ""

    if argone == "inv":
        argf = "filtered"
        argone = "noarguser"
    elif argtwo == "inv":
        argf = "filtered"
        argtwo = "noarguser"
    elif "inv" in argv:
        argf = "filtered"

    if argone == "search":  # recentchanges search
        thetime = argtwo
        return recentchanges_main(argone, thetime, usr, pwd, argf, method)

    else:  # recentchanges

        thetime = argone  # shift for recentchanges
        method = "rnt"

        if thetime == "SRC":
            thetime = argtwo if argtwo != "SRC" else "noarguser"

        if argtwo == "search":
            print("Exiting not a search.")
            return 1

        srcDIR = "SRC" if "SRC" in sys.argv else "noarguser"

        return recentchanges_main(thetime, srcDIR, usr, pwd, argf, method)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
