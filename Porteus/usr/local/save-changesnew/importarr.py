# array processing future method  09/13/2025
import pyfunctions
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

def read_file_lines(path):
    p = Path(path)
    return [line.rstrip() for line in p.open()] if p.is_file() and p.stat().st_size > 0 else []

def timestamp_from_line(line):
    parts = line.split()
    return " ".join(parts[:2])

def parse_ts(ts):
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

def extract_quoted(line):
    m = re.search(r'"((?:[^"\\]|\\.)*)"', line)
    return m.group(1) if m else ""

def line_included(line, patterns):
    return not any(p in line for p in patterns)


def importarr(SORTCOMPLETE, tout, flsrh, noarguser, argone, updatehlinks, TMPOUTPUT, TMPOPT, RECENT, usr, logpst, statpst, pydbpst):

      exclude_patterns = [
            r"/usr/local/save-changesnew/flth\.csv",
            rf"/home/{usr}/Downloads/rnt",
            logpst,
            statpst,
            pydbpst
      ]

      lines = read_file_lines(SORTCOMPLETE)
      lines = sorted(set(lines), key=lambda l: parse_ts(timestamp_from_line(l)))

      SRTTIME = timestamp_from_line(lines[0]) if lines else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      PRD = SRTTIME

      tout_lines = read_file_lines(tout)
      lines += [l for l in tout_lines if timestamp_from_line(l) >= PRD]

      lines = [l for l in lines if line_included(l, exclude_patterns)]
      lines = sorted(set(lines), key=lambda l: parse_ts(timestamp_from_line(l)))

      if updatehlinks == "true":
            print(f'{pyfunctions.GREEN}Updating hardlinks{pyfunctions.RESET}')

            try:
                  subprocess.run(
                        ['/usr/local/save-changesnew/ulink.sh', SORTCOMPLETE, tout, TMPOPT],
                        check=True
                  )
            except subprocess.CalledProcessError as e:
                  print(f"Failed to get hardlinks in importarr py: {e}")


      if flsrh == "false" or flsrh == "rnt":
            start_dt = parse_ts(SRTTIME)
            range_sec = 300 if noarguser == 'noarguser' else int(argone)
            end_dt = start_dt + timedelta(seconds=range_sec)
            lines = [l for l in lines if parse_ts(timestamp_from_line(l)) <= end_dt]

      timestamps = [timestamp_from_line(l) for l in lines]
      quoted_strings = [extract_quoted(l) for l in lines]

      combined_all = [f"{ts} {q}" for ts, q in zip(timestamps, quoted_strings)]

      tmparr = []

      for line in lines:
            quoted_match = re.search(r'"((?:[^"\\]|\\.)*)"', line)
            if not quoted_match:
                  continue
            filepath = quoted_match.group(1)  # unquoted
            line_without_file = line.replace(quoted_match.group(0), '').strip()
            other_fields = line_without_file.split()
            if len(other_fields) < 2:
                  continue
            field1 = other_fields[0]
            field2 = other_fields[1]
            tmparr.append(f"{field1} {field2} {filepath}")


      tmp_lines = [l for l in tmparr if l.split(" ", 2)[2].startswith("/tmp")]
      tmparr_non_tmp = [l for l in tmparr if not l.split(" ", 2)[2].startswith("/tmp")]

      if flsrh != "rnt":  # 'recentchanges search' only
            SORTCOMPLETE_ARRAY = [l for l in lines if not extract_quoted(l).startswith("/tmp")]

            # human readable sortcomplete sans /tmp search files
            with open(TMPOPT, "w") as f:
                  f.write("\n".join(tmparr_non_tmp))    

            # /tmp search files
            with open(TMPOUTPUT, "w") as f:
                  f.write("\n".join(tmp_lines))

            # used for filter hits the complete list  Handle in bash
            # with open(RECENT, "w") as f:
            #       f.write("\n".join(tmparr_non_tmp))

      else:  # 'recentchanges'
            SORTCOMPLETE_ARRAY = lines
            with open(TMPOPT, "w") as f:
                  f.write("\n".join(tmparr))


      return SORTCOMPLETE_ARRAY




