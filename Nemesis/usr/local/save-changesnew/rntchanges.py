#!/usr/bin/env python3
# v5.0                                                       02/26/2026
# This script is the entry point for recentchanges. The inv flag is passed in from from /usr/local/save-changesnew/filteredsearch script from /usr/local/bin/rnt symlink
#
# There are 2 positional arguments. a third is the inv flag and is filtered out before executing script.
# the filtered arg just changes a regular search to the inverse for `recentchanges search`, `recentchanges search n`, `recentchanges search myfile`
#
# for `recentchanges` the arguments shift. as its `recentchanges` or `recentchanges n` and the filter arg doesnt apply. There is a SRC tag which will make a .xzm
# from a root directory with the most recent files.
# `recentchanges` takes 1 argument the time n or no arguments for 5 minutes.
#
# `recentchanges search` - Desktop unfiltered files and tmp files. Also search for newer than file filtered. if called from rnt.bat its the opposite.
# `query` - show stats from the database from past searches
#
# `recentchanges` - AppData unfiltered and archives searches. No tmp files.


# argone - the search time for `recentchanges` or the keyword search for `recentchanges search` or keyword query to get stats from database
# argtwo - search time for `recentchanges search`
# argf - inv flag from rnt symlink
import sys
from query import main as query_main
from recentchangessearch import main as recentchanges_main


# Handle inv flag
def filter_invflag(argv, pad_length=5):

    arge = ["" if item == "inv" else item for item in argv]
    argf = "filtered" if "inv" in argv else ""

    if len(arge) < pad_length:
        arge.extend([""] * (pad_length - len(arge)))
    return arge, argf


def main(argv):

    inv_flag = "inv" in argv
    max_len = 6 if inv_flag else 5
    if len(argv) > max_len:
        if inv_flag:
            print("Incorrect usage. max from rnt 6. provided: ", len(argv) - 1)
        else:
            print("Incorrect usage. max args 5. provided: ", len(argv) - 1)
        print("Required <USR> <PWD>")
        print("please call from /usr/local/bin/recentchanges")
        return 1
    if len(argv) < 3:
        print("Incorrect usage. <USR> <PWD>")
        return 1

    USR = argv[1]  # USR = os.getenv("USR")
    PWD = argv[2]  # os.getcwd()
    args = argv[3:]

    arge, argf = filter_invflag(args)  # filter out the invflag set argf to `filtered`. passed from filteredsearch

    argone = arge[0] or "noarguser"
    THETIME = arge[1] or "noarguser"

    if argone == "search":  # recentchanges search
        return recentchanges_main(argone, THETIME, USR, PWD, argf, "")

    elif argone == "reset":
        return query_main(USR, reset=True)
    else:  # recentchanges
        argf = "bnk"

        SRCDIR = "SRC" if "SRC" in arge[:2] else "noarguser"

        THETIME = arge[0] or "noarguser"  # Shift for this script
        if THETIME == "SRC":
            THETIME = arge[1] or "noarguser"

        if THETIME == "search":
            print("Exiting not a search.")
            return 1

        if THETIME == "SRC":
            THETIME = "noarguser"

        return recentchanges_main(THETIME, SRCDIR, USR, PWD, argf, "rnt")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
