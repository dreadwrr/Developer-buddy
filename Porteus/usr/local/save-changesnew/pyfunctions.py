import csv                                                                                              #11/28/2025
import fnmatch
import re
from datetime import datetime

# terminal and hardlink supression
supress_terminal = [
    r'mozilla',
    r'\.mozilla',
    r'chromium-ungoogled',
    r'/home/{{user}}/\.cache/somefolder'
    #r'google-chrome',  
]

# Cache clear
# patterns to delete
cache_clear = [
    "%caches%",
    "%cache2%",
    "%Cache2%",
    "%.cache%",
    "%share/Trash%",
    f"%home/{{user}}/.local/state/wireplumber%",
    "%usr/share/mime/application%",
    "%usr/share/mime/text%",
    "%usr/share/mime/image%",
    "%release/cache%",
]

# filter hits to reset on cache clear. copy from items to reset from filter.py
flth_literal_patterns = [
    r'/home/{user}/.Xauthority',
    r'/home/{user}/.local/state/wireplumber'
]


def sbwr(escaped_user): 
    supress_list = [p.replace("{{user}}", escaped_user) for p in supress_terminal]
    compiled = [re.compile(p) for p in supress_list ]
    return compiled


def get_delete_patterns(usr): 
    patterns = [p.replace("{user}", usr) for p in cache_clear]
    return patterns

def reset_csvliteral(csv_file):

    patterns_to_reset = flth_literal_patterns

    with open(csv_file, newline='') as f:
        reader = csv.reader(f)
        rows = list(reader)
    for row in rows[1:]:
        if row[0] in patterns_to_reset:
            row[1] = '0' 
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)


class cprint:
    CYAN = "\033[36m"
    RED = "\033[31m"
    GREEN = "\033[1;32m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    YELLOW = "\033[33m"
    WHITE = "\033[37m"
    RESET = "\033[0m"

    @staticmethod
    def cyan(msg):
        print(f"{cprint.CYAN}{msg}{cprint.RESET}")

    @staticmethod
    def red(msg):
        print(f"{cprint.RED}{msg}{cprint.RESET}")

    @staticmethod
    def green(msg):
        print(f"{cprint.GREEN}{msg}{cprint.RESET}")

    @staticmethod
    def blue(msg):
        print(f"{cprint.BLUE}{msg}{cprint.RESET}")

    @staticmethod
    def yellow(msg):
        print(f"{cprint.YELLOW}{msg}{cprint.RESET}")

    @staticmethod
    def magenta(msg):
        print(f"{cprint.MAGENTA}{msg}{cprint.RESET}")

    @staticmethod
    def white(msg):
        print(f"{cprint.WHITE}{msg}{cprint.RESET}")

    @staticmethod
    def reset(msg):
        print(f"{cprint.RESET}{msg}")

# after file is inserted. in ha its not inserted yet
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

#11/29/2025
def detect_copy(filename, inode, checksum, cursor, ps):
    if ps:
        query = f'''
            SELECT filename, inode
            FROM logs
			WHERE checksum = ?
            UNION ALL
            SELECT filename, inode
            FROM sys
            WHERE checksum = ?
        '''
        cursor.execute(query, (checksum, checksum))
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


def get_recent_sys(filename, cursor, sys_table, e_cols=None):

    columns = [
        "timestamp", "filename", "changetime", "inode",
        "accesstime", "checksum", "filesize", "owner",
        "`group`", "permissions"
    ]
    if e_cols:
        if isinstance(e_cols, str):
            e_cols = [col.strip() for col in e_cols.split(',') if col.strip()]
        columns += e_cols

    col_str = ", ".join(columns)

    cursor.execute(f'''
        SELECT {col_str}
        FROM {sys_table}
        WHERE filename = ?
        ORDER BY timestamp DESC
        LIMIT 1
    ''', (filename,))
    row = cursor.fetchone()
    return row
    # if row:
        # return row
    # cursor.execute(f'''
    #     SELECT {col_str}
    #     FROM {sys_a}
    #     WHERE filename = ?
    #     LIMIT 1
    # ''', (filename,))
    # return cursor.fetchone()


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


def increment_f(conn, c, records):
    # batch insert into sys in one go
    if not records:
        return

    sql_insert= f"""
        INSERT INTO sys (
            timestamp, filename, changetime, inode, accesstime, checksum,
            filesize, symlink, owner, `group`, permissions, casmod, lastmodified,
			count, escapedpath
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    try:
        c.executemany(sql_insert, records)
        
        sql_update = "UPDATE sys SET count = CAST(count AS INTEGER) + 1 WHERE filename = ?" #f"UPDATE sys SET count = count + 1 WHERE filename = ?"     its TEXT tk sorting problems as INT
        filenames = [(record[1],) for record in records]
        c.executemany(sql_update, filenames)
        conn.commit()
        
        return True

    except Exception as e:
        conn.rollback()
        print(f"Error {type(e).__name__} : {e}")
        return False

# Update sys table counts          10/07/2025 typofix innerfor
# def ucount(conn, cur):
#     cur.execute('''
#         SELECT filename, COUNT(*) as total_count
#         FROM sys
#         GROUP BY filename
#         HAVING total_count > 1
#     ''')
#     duplicates = cur.fetchall()
#     for filename, total_count in duplicates:
#         cur.execute('''
#             UPDATE sys
#             SET count = ?
#             WHERE filename = ?
#         ''', (total_count, filename))
#     conn.commit()
# if many sys files but no need
#  updates = [(total_count, filename) for filename, total_count in duplicates]
# cur.executemany('''
#     UPDATE sys
#     SET count = ?
#     WHERE filename = ?
# ''', updates)

def matches_any_pattern(s, patterns):
    # Convert SQL-like % wildcard to fnmatch *
    for pat in patterns:
        pat = pat.replace('%', '*')
        if fnmatch.fnmatch(s, pat):
            return True
    return False

def epoch_to_date(epoch):
    try:
        return datetime.fromtimestamp(float(epoch))
    except(TypeError, ValueError):
        return None

def parse_datetime(value, fmt="%Y-%m-%d %H:%M:%S"):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(str(value).strip(), fmt)
    except (ValueError, TypeError, AttributeError):
        return None

def escf_py(filename):
    filename = filename.replace('\\', '\\\\')
    filename = filename.replace('\n', '\\n')
    filename = filename.replace('"', '\\"')
    filename = filename.replace('$', '\\$')
    return filename
#10/07/2025
def unescf_py(s):
    s = s.replace('\\n', '\n')
    s = s.replace('\\"', '"')
    s = s.replace('\\$', '$')
    s = s.replace('\\\\', '\\')
    return s
#def unescf_py(escaped):   old
#    s = escaped
#    s = s.replace('\\\\', '\\')
#    s = s.replace('\\n', '\n')
#    s = s.replace('\\"', '"') 
#    s = s.replace('\\$', '$')     
#    return s

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

def sys_record_flds(record, sys_records, prev_count):
    sys_records.append((
        record[0],  # timestamp
        record[1],  # filename
        record[2],  # changetime
        record[3],  # inode
        record[4],  # accesstime
        record[5],  # checksum
        record[6],  # filesize
        record[7],  # symlink
        record[8],  # owner
        record[9],  # group
        record[10], # permissions
        record[11], # casmod
        record[12], # lastmodified
        prev_count, # count
        record[14] # escapedpath
    ))

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

def new_meta(record, metadata):
    return (
        record[10] != metadata[2] or # perm
        record[8]  != metadata[0] or # onr
        record[9]  != metadata[1] # grp
    )

def getstdate(st, fmt):
	a_mod = int(st.st_mtime)
	afrm_str = datetime.fromtimestamp(a_mod).strftime(fmt)  # datetime.utcfromtimestamp(a_mod).strftime(fmt)
	afrm_dt = parse_datetime(afrm_str, fmt)
	return afrm_dt, afrm_str

#pstsrg
def goahead(filepath):
    try:
        st = filepath.stat()
        return st
    except FileNotFoundError:
        return "Nosuchfile"
    except (PermissionError, OSError, Exception) as e:
         pass
        #print(f"Skipping {filepath.name}: {type(e).__name__} - {e}")
    return None
