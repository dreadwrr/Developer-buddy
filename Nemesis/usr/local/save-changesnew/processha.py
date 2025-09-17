import re
import datetime
import os
from pyfunctions import sbwr
from recentchangessearch import filter_lines_from_list

def parse_timestamp(line):
    timestamp_str = line.split()[1]  # field 1
    return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

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
                    pricolor(f"{file_line} {typ}")
            else:
                if critical != "no":
                    if file_line.startswith(critical) or file_line.startswith("COLLISION"):
                        seccolor(f'{file_line} {typ} Critical')
                        flg = True
                else:
                    seccolor(f"{file_line} {typ}")

def processha(rout, ABSENT, difffile, cerr, TMPOPT, flsrh, lclmodule, argf, USR, supbrwr, supress):
    cleaned_rout = []

    for line in rout:
        parts = line.strip().split(" ", 3)
        if len(parts) < 4:
            continue

        if parts[0] == "Nosuchfile":
            continue  # Skip lines starting with 'Nosuchfile'

        action, timestamp, _, filepath = parts
        cleaned_line = f'{action} {timestamp} {filepath}'
        cleaned_rout.append(cleaned_line)

    absent_paths = {line.rsplit(" ", 1)[-1] for line in ABSENT}

    DIFFMATCHED = [
        line for line in cleaned_rout
        if line.rsplit(" ", 1)[-1] not in absent_paths
    ]

    if flsrh or argf == "filtered":
        if not ( flsrh and argf == "filtered"):
            DIFFMATCHED = filter_lines_from_list(DIFFMATCHED, user=USR)

    if flsrh:
        start_time = parse_timestamp(TMPOPT[0].split()[1])
        DIFFMATCHED = [line for line in TMPOPT if parse_timestamp(line) >= start_time]

    with open(difffile, 'a') as f:
        for line in DIFFMATCHED:
            fields = line.split(None, 3)
            if len(fields) < 4:
                continue

            field1 = fields[0]
            field2_3 = f"{fields[1]} {fields[2]}"
            rest = fields[3]

            # replicate awk formatting:
            # %-9s\t%-19s %s\n
            formatted_line = f"{field1:<9}\t{field2_3:<19} {rest}\n"
            f.write(formatted_line)


    if os.path.exists(cerr):

        filter_output(cerr, lclmodule, 'Warning', 'Suspect', 'yellow', 'red', 'elevated', supbrwr, supress)
        return True
    
    return False





