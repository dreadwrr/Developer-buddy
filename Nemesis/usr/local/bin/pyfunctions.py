#!/usr/bin/env python3
import re
import codecs
CYAN = "\033[36m"
RED = "\033[31m"
GREEN = "\033[1;32m"
YELLOW = "\033[33m"
RESET = "\033[0m"
def getcount (curs):
      curs.execute('''
            SELECT COUNT(*)
            FROM logs
            WHERE (timestamp IS NULL OR timestamp = '')
            AND (filename IS NULL OR filename = '')
            AND (inode IS NULL OR inode = '')
            AND (accesstime IS NULL OR accesstime = '')
            AND (checksum IS NULL OR checksum = '')
            AND (filesize IS NULL OR filesize = '')
      ''')
      count = curs.fetchone()
      value=count[0]
      return value
def parse_line(line):
      quoted_match = re.search(r'"((?:[^"\\]|\\.)*)"', line)
      if not quoted_match:
            return None
      raw_filepath = quoted_match.group(1)
      try:
            filepath = codecs.decode(raw_filepath.encode(), 'unicode_escape')
            #print(f"Decoded filepath: {filepath}")
      except UnicodeDecodeError as e:
            #print(f"Error decoding filepath: {e}")
            return None
      line_without_file = line.replace(quoted_match.group(0), '').strip()
      other_fields = line_without_file.split()
      if len(other_fields) < 5:
            return None  # Not enough fields
      timestamp1 = other_fields[0] + ' ' + other_fields[1]
      inode = other_fields[2]
      timestamp2 = other_fields[3] + ' ' + other_fields[4]
      rest = other_fields[5:]
      return [timestamp1, filepath, inode, timestamp2] + rest