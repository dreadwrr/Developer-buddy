#!/bin/env python3          
#   manipulate array before database srg and send output to diff file             09/17/2025
import datetime
import os

from rntchangesfunctions import filter_output 
from rntchangesfunctions import filter_lines_from_list
from pyfunctions import parse_datetime

def parse_timestamp(line):

    timestamp_str = " ".join(line.split()[:2])
    return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")


# postprocess
def isdiff(RECENT, ABSENT, rout, diffnm, difff_file, flsrh, parsed_PRD, uid, fmt):
    def insert(ABSENT, rout, line, file2, res):
        res = True
        print(line, file=file2)
        if filepath in d_paths:
            ABSENT.append(f"Modified {line}")
        else:
            ABSENT.append(f"Deleted {line}")
            rout.append(f"Deleted {timestamp_str} {line}")
        return res

    res = False
    d_paths = set(line.strip().split(" ", 2)[-1] for line in RECENT)

    with open(diffnm, 'a') as file2:
        
        for line in difff_file:
            
            parts = line.strip().split(" ", 2)
            if len(parts) < 3:
                continue
            timestamp_str = parts[0] + " " + parts[1]
            timestamp = parse_datetime(timestamp_str, fmt)
            if timestamp is None:
                continue
            
            filepath = parts[2]

            if flsrh == "false":
                if timestamp >= parsed_PRD:
                    res=insert(ABSENT, rout, line, timestamp_str, d_paths, file2, res)
            else:
                res=insert(ABSENT, rout, line, timestamp_str, d_paths, file2, res)
        if res:
            if ABSENT:
                file2.write('\nApplicable to your search\n')
            else:
                print('None of above is applicable to search. It is the previous search', file=file2)
            os.chown(diffnm, uid, -1)



# output
def processha(rout, ABSENT, diffnm, cerr, flsrh, lclmodule, argf, parsed_PRD, USR, supbrwr, supress):

    cleaned_rout = []
    if rout:
        with open(diffnm, 'a') as f:
            print(file=f)
            f.write("Hybrid analysis\n\n\n")

            for line in rout:
                parts = line.strip().split(" ", 3)
                if len(parts) < 4:
                    continue
                if parts[0] in ("Deleted", "Nosuchfile"):
                        continue 
                action, timestamp, _, filepath = parts
                cleaned_line = f'{action} {timestamp} {filepath}'
                cleaned_rout.append(cleaned_line)

            absent_paths = {line.rsplit(" ", 1)[-1] for line in ABSENT}

            DIFFMATCHED = [
                line for line in cleaned_rout
                if line.rsplit(" ", 1)[-1] not in absent_paths
            ]


            if flsrh == "true" or argf == "filtered":
                if not ( flsrh and argf == "filtered"):
                    DIFFMATCHED = filter_lines_from_list(DIFFMATCHED, user=USR)

            
            for line in DIFFMATCHED:
                fields = line.split(None, 3)
                if len(fields) < 4:
                    continue

                field1 = fields[0]
                field2_3 = f"{fields[1]} {fields[2]}"
                rest = fields[3]

                if flsrh == "true":
                    ts = parse_datetime(field2_3)
                    if ts is None or ts < parsed_PRD:
                        continue

                formatted_line = f"{field1:<9}\t{field2_3:<19} {rest}\n"
                f.write(formatted_line)


    if os.path.exists(cerr):

        filter_output(cerr, lclmodule, 'Warning', 'Suspect', 'yellow', 'red', 'elevated', supbrwr, supress)
        return True
    
    return False





