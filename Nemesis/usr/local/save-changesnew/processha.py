#!/bin/env python3          
#   manipulate array before database srg and send output to diff file             09/20/2025
import os

from pyfunctions import parse_datetime
from rntchangesfunctions import changeperm
from rntchangesfunctions import filter_output 
from rntchangesfunctions import filter_lines_from_list

def get_timestamp(line):
    parts = line.strip().split(None, 2)
    if len(parts) < 2:
        return None
    return parse_datetime(parts[1]) 


# preprocess diff file
def isdiff(RECENT, ABSENT, rout, diffnm, difff_file, flsrh, parsed_PRD, uid, fmt):

    ranged = []

    if flsrh == "false":

        for line in difff_file:
            parts = line.strip().split(" ", 1)
            if not parts:
                continue

            timestp = parse_datetime(parts[0], fmt)
            if timestp is None:
                continue

            if timestp >= parsed_PRD:
                ranged.append(line)
    else:
        ranged = difff_file[:]

    if ranged:
        d_paths = set(line.strip().split(" ", 2)[-1] for line in RECENT)

        with open(diffnm, 'a') as file2:
            for line in ranged:
                parts = line.strip().split(" ", 2)
                if len(parts) < 3:
                    continue
                timestamp_str = parts[0] + " " + parts[1]
                timestamp = parse_datetime(timestamp_str, fmt)
                if timestamp is None:
                    continue
                
                filepath = parts[2]

                if filepath in d_paths:           
                    ABSENT.append(f"Modified {line}")             

                else:
                    ABSENT.append(f"Deleted {line}")
                    rout.append(f"Deleted {timestamp} {timestamp} {line}")

            if ABSENT:
                
                file2.write('\nApplicable to your search\n')
                file2.write('\n'.join(ABSENT) + '\n')

    else:
        with open(diffnm, 'a') as file2:
            print('None of above is applicable to search. It is the previous search', file=file2)       

    changeperm(diffnm, uid)

   
# post ha to diff
def processha(rout, ABSENT, diffnm, cerr, flsrh, lclmodule, argf, parsed_PRD, USR, supbrwr, supress):
    cleaned_rout = []
    outline = []

    if rout:
        for line in rout:
            parts = line.strip().split(None, 3)
            if len(parts) < 4:
                continue
            if parts[0] in ("Deleted", "Nosuchfile"):
                continue

            action, timestamp, _, filepath = parts
            cleaned_line = f"{action} {timestamp} {filepath}"
            cleaned_rout.append(cleaned_line)


        if ABSENT:
            absent_paths = {line.strip().split(None, 3)[-1] for line in ABSENT}
            DIFFMATCHED = [
                line for line in cleaned_rout
                if line.strip().split(None, 3)[-1] not in absent_paths
            ]
        else:
            DIFFMATCHED = cleaned_rout[:]

     
        DIFFMATCHED = [
            line for line in DIFFMATCHED
            if get_timestamp(line) is not None
        ]


        if (flsrh == "true" or argf == "filtered") and not (flsrh == "true" and argf == "filtered"):
            DIFFMATCHED = filter_lines_from_list(DIFFMATCHED, USR)


        if flsrh:
            DIFFMATCHED = [
                line for line in DIFFMATCHED
                if (ts := get_timestamp(line)) and ts >= parsed_PRD
            ]


        DIFFMATCHED.sort(key=get_timestamp)

        for line in DIFFMATCHED:
            fields = line.split(None, 2)
            if len(fields) < 3:
                continue
            field1, field2_3, rest = fields
            formatted_line = f"{field1:<9}\t{field2_3:<19} {rest}\n"
            outline.append(formatted_line)

    if outline:
        with open(diffnm, 'a') as f:
            f.write('\nHybrid analysis\n\n')
            f.writelines(outline)

    if os.path.exists(cerr):
        filter_output(cerr, lclmodule, 'Warning', 'Suspect', 'yellow', 'red', 'elevated', supbrwr, supress)
        return True

    return False






