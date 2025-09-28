#!/bin/env python3          
#   manipulate array before database srg and send output to diff file             09/26/2025
import os
from pyfunctions import parse_datetime
from rntchangesfunctions import filter_output 
from rntchangesfunctions import filter_lines_from_list

def get_trout(line):
    parts = line.strip().split(None, 3)
    if len(parts) < 3:
        return None
    tsmp=f'{parts[1]} {parts[2]}'
    return parse_datetime(tsmp) 

# preprocess diff file
def isdiff(RECENT, ABSENT, rout, diffnm, difff_file, flsrh, parsed_PRD, fmt):

    ranged = []

    if not flsrh:

        for line in difff_file:
            parts = line.strip().split(None, 2)
            if not parts:
                continue
            tsmp = f'{parts[0]} {parts[1]}'
            timestp = parse_datetime(tsmp, fmt)
            if timestp is None:
                continue

            if timestp >= parsed_PRD:
                ranged.append(line)
    else:
        ranged = difff_file[:]

    if ranged:
        d_paths = set(entry[1] for entry in RECENT)

        with open(diffnm, 'a') as file2:
            for line in ranged:
                parts = line.strip().split(None, 2)
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

   
# post ha to diff
def processha(rout, ABSENT, diffnm, cerr, flsrh, lclmodule, argf, parsed_PRD, USR, supbrwr, supress, fmt):
    cleaned_rout = []
    outline = []

    if rout:

        for line in rout:
            parts = line.strip().split()
            if len(parts) < 6:
                continue
            if parts[0] in ("Deleted", "Nosuchfile"):
                continue
            action = parts[0]
            ts1 = f'{parts[1]} {parts[2]}'
            fpath = ' '.join(parts[5:])
            cleaned_line = f'{action} {ts1} {fpath}'
            cleaned_rout.append(cleaned_line)


        absent_paths = {line.strip().split(None, 3)[-1] for line in ABSENT}
        DIFFMATCHED = [
            line for line in cleaned_rout
            if line.strip().split(None, 3)[-1] not in absent_paths
        ]

        if flsrh  or argf == "filtered":
            if not (flsrh  and argf == "filtered"):
                DIFFMATCHED = filter_lines_from_list(DIFFMATCHED, USR)


        if flsrh:
            DIFFMATCHED = [
                line for line in DIFFMATCHED
                if (ts := get_trout(line)) and ts >= parsed_PRD
            ]


        DIFFMATCHED.sort(key=get_trout)

        for line in DIFFMATCHED:
            fields = line.split()
            if len(fields) < 4:
                continue

            status = fields[0]         
            date = fields[1]           
            time = fields[2]             
            path = " ".join(fields[3:]) 

            formatted_line = f"{status:<9} {date} {time} {path}\n"
            outline.append(formatted_line)


    if outline:
        with open(diffnm, 'a') as f:
            f.write('\nHybrid analysis\n\n')
            f.writelines(outline)

    if os.path.exists(cerr):
        filter_output(cerr, lclmodule, 'Warning', 'Suspect', 'yellow', 'red', 'elevated', supbrwr, supress)
        return True

    return False






