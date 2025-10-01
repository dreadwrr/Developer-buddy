import fnmatch
import hashlib
import os
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
def detect_copy(filename, inode, checksum, cursor, sys_table):
    # Step 1: select candidates by checksum only (index-friendly)
    if sys_table == 'sys':
        query = '''
            SELECT filename, inode, checksum
            FROM logs
            UNION ALL
            SELECT filename, inode, checksum
            FROM sys
            WHERE checksum = ?
        '''
    else:
        query = '''
            SELECT filename, inode
            FROM logs
            WHERE checksum = ?
        '''
    
    cursor.execute(query, (checksum,))
    candidates = cursor.fetchall()
    
    for o_filename, o_inode in candidates:
        if o_filename != filename or o_inode != inode:
            return True
    
    return None
def get_recent_changes(filename, cursor, table):
	allowed_tables = ('logs', 'sys')
	if table not in allowed_tables:
		return None
	query = f'''
		SELECT timestamp, filename, changetime, inode, accesstime, checksum, filesize, owner, `group`, permissions
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
    c.execute('''
        INSERT OR IGNORE INTO sys (
            timestamp, filename, changetime, inode, accesstime, checksum,
            filesize, symlink, owner, `group`, permissions, casmod, count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    ''', (
        record[0], filename, record[2], record[3],
        record[4], record[5], record[6], record[7],
        record[8], record[9], record[10], record[11]
    ))
    c.execute('''
        UPDATE sys
        SET count = count + 1
        WHERE filename = ? AND timestamp != ? AND changetime != ?
    ''', (filename, record[0], record[2]))
    

def matches_any_pattern(s, patterns):
    # Convert SQL-like % wildcard to fnmatch *
    for pat in patterns:
        pat = pat.replace('%', '*')
        if fnmatch.fnmatch(s, pat):
            return True
    return False
    
def parse_datetime(value, fmt):
	try:
		return datetime.strptime(str(value).strip(), fmt)
		#return dt.strftime(fmt)
	except (ValueError, TypeError, AttributeError):
		return None

def escf_py(filename):
    filename = filename.replace('\\', '\\\\')
    filename = filename.replace('\n', '\\n')
    filename = filename.replace('"', '\\"')
    filename = filename.replace('$', '\\$')
    return filename

def unescf_py(escaped):
    s = escaped
    s = s.replace('\\\\', '\\')
    s = s.replace('\\n', '\n')
    s = s.replace('\\"', '"') 
    s = s.replace('\\$', '$')     
    return s

def parse_line(line):
    quoted_match = re.search(r'"((?:[^"\\]|\\.)*)"', line)
    if not quoted_match:
        return None
    raw_filepath = quoted_match.group(1)
    # try:
    #     filepath = codecs.decode(raw_filepath.encode(), 'unicode_escape')
    # except UnicodeDecodeError:
    #     filepath = raw_filepath
    filepath = unescf_py(raw_filepath)

    # Remove quoted path 
    line_without_file = line.replace(quoted_match.group(0), '').strip()
    other_fields = line_without_file.split()

    if len(other_fields) < 7:
        return None

    timestamp1 = other_fields[0] + ' ' + other_fields[1]
    timestamp2 = other_fields[2] + ' ' + other_fields[3]
    inode = other_fields[4]
    timestamp3 = other_fields[5] + ' ' + other_fields[6]
    rest = other_fields[7:]

    return [timestamp1, filepath, timestamp2, inode, timestamp3] + rest

# return filenm
def getnm(locale, ext=''):
      root = os.path.basename(locale)
      root, ext = os.path.splitext(root)
      return root + ext

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
def is_valid_datetime(value, fmt):
	try: 
		datetime.strptime(str(value).strip(), fmt)
		return True
	except (ValueError, TypeError, AttributeError):
		return False
     
def log_event(event, record, label, file_full, file_short):
    msg_full = f'{event} {record[0]} {record[2]} {label}'
    print(msg_full, file=file_full)
    #print(msg_short, file=file_short)
     #msg_short = f'{event} {record[0]} {label}'

def new_meta(record, metadata):
    return (
        record[10] != metadata[2] or # perm
        record[8]  != metadata[0] or # onr
        record[9]  != metadata[1] # grp
    )

def goahead(filepath):
	try:
		st = filepath.stat()
		return st
	except (FileNotFoundError, PermissionError, OSError, Exception) as e:
		print(f"Skipping {filepath.name}: {type(e).__name__} - {e}")
		return None
     
def getstdate(st, fmt):
	a_mod = int(st.st_mtime)
	afrm_str = datetime.utcfromtimestamp(a_mod).strftime(fmt)
	afrm_dt = parse_datetime(afrm_str, fmt)
	return afrm_dt, afrm_str