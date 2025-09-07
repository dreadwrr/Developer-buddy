import codecs
import fnmatch
import hashlib
import re
from datetime import datetime
CYAN = "\033[36m"
RED = "\033[31m"
GREEN = "\033[1;32m"
YELLOW = "\033[33m"
RESET = "\033[0m"
def get_delete_patterns(usr, dbp): # db cache clr
    return [
        "%caches%",
        "%cache2%",
        "%Cache2%",
        "%.cache%",
        "%share/Trash%",
        f"%home/{usr}/Downloads/rntfiles%",
        f"%home/{usr}/.local/state/wireplumber%",
        "%usr/share/mime/application%",
        "%usr/share/mime/text%",
        "%usr/share/mime/image%",
        "%release/cache%",
        f"%{dbp}%",
        "%usr/local/save-changesnew/flth.csv%",
    ]
	# cursor.execute('''
	# SELECT a.filename, b.filename, a.checksum, a.filesize, b.filesize
	# FROM logs a
	# JOIN logs b
	# 	ON a.checksum = b.checksum
	# 	AND a.filename != b.filename
	# WHERE a.filesize != b.filesize
	# 	AND a.filename = ?
	# ''', (filename,))
def collision(filename, checksum, filesize, cursor, sys):
    if sys:
        query = '''
            WITH combined AS (
                SELECT filename, checksum, filesize FROM logs
                UNION ALL
                SELECT filename, checksum, filesize FROM sys
            )
            SELECT b.filename, a.checksum, a.filesize, b.filesize
            FROM combined a
            JOIN combined b
            ON a.checksum = b.checksum
            AND a.filename != b.filename
            WHERE a.filename = ?
            AND a.checksum = ?
            AND b.filesize != ?
        '''
    else:
        table_name='logs'
        query = f'''
            SELECT b.filename, a.checksum, a.filesize, b.filesize
            FROM {table_name} a
            JOIN {table_name} b
            ON a.checksum = b.checksum
            AND a.filename != b.filename
            WHERE a.filename = ?
            AND a.checksum = ?
            AND b.filesize != ?
        '''
    cursor.execute(query, (filename, checksum, filesize))
    return cursor.fetchall()
def get_recent_changes(filename, cursor, table):
	allowed_tables = ('logs', 'sys')
	if table not in allowed_tables:
		return None
	query = f'''
		SELECT timestamp, filename, inode, accesstime, checksum, filesize, changetime
		FROM {table}
		WHERE filename = ?
		ORDER BY timestamp DESC
		LIMIT 1
	'''
	cursor.execute(query, (filename,))
	reslt = cursor.fetchone()
	return reslt
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
      return count[0]
def increment_fname(conn, c, record):
    filename = record[1]
    c.execute('SELECT count FROM sys WHERE filename = ?', (filename,))
    row = c.fetchone()
    current_count = (row[0] if row else 0) + 1
    c.execute('''
        INSERT OR REPLACE INTO sys (
            timestamp, filename, inode, accesstime, checksum, filesize, symlink, owner, `group`, permissions, changetime, casmod, count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        record[0], filename, record[2], record[3],
        record[4], record[5], record[6], record[7],
        record[8], record[9], record[10], record[11],
        current_count
    ))
    conn.commit()

def matches_any_pattern(s, patterns):
    # Convert SQL-like % wildcard to fnmatch *
    for pat in patterns:
        pat = pat.replace('%', '*')
        if fnmatch.fnmatch(s, pat):
            return True
    return False
    
def parse_datetime(value, fmt="%Y-%m-%d %H:%M:%S"):
	try:
		return datetime.strptime(str(value).strip(), fmt)
		#return dt.strftime(fmt)
	except (ValueError, TypeError, AttributeError):
		return None

def parse_line(line):
    quoted_match = re.search(r'"((?:[^"\\]|\\.)*)"', line)
    if not quoted_match:
        return None
    raw_filepath = quoted_match.group(1)
    try:
        filepath = codecs.decode(raw_filepath.encode(), 'unicode_escape')
    except UnicodeDecodeError:
        filepath = raw_filepath  # Fallback to raw path if decoding fails

    # Remove quoted path 
    line_without_file = line.replace(quoted_match.group(0), '').strip()
    other_fields = line_without_file.split()

    if len(other_fields) < 5:
        return None  # Not enough fields

    timestamp1 = other_fields[0] + ' ' + other_fields[1]
    inode = other_fields[2]
    timestamp2 = other_fields[3] + ' ' + other_fields[4]
    rest = other_fields[5:]

    return [timestamp1, filepath, inode, timestamp2] + rest
def get_md5(file_path):
    try:
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None 
def is_integer(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False
def is_valid_datetime(value, fmt="%Y-%m-%d %H:%M:%S"):
	try: 
		datetime.strptime(str(value).strip(), fmt)
		return True
	except (ValueError, TypeError, AttributeError):
		return False