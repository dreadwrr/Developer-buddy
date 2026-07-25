import fnmatch
import hashlib
import os
import subprocess
import traceback
from collections import defaultdict
from datetime import datetime

# Cache clear patterns to delete from db - see /usr/local/save-changesnew/clearcache to reset filter hits ln33

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
    "%release/cache%"
]

CYAN = "\033[36m"
RED = "\033[31m"
GREEN = "\033[1;32m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def get_delete_patterns(usr):  # db cache clr
    patterns = [p.replace("{user}", usr) for p in cache_clear]
    return patterns


def collision(cursor, is_sys):
    try:
        if is_sys:
            tables = ['logs', 'sys']
            union_sql = " UNION ALL ".join([
                f"SELECT filename, checksum, filesize FROM {t} WHERE checksum IS NOT NULL" for t in tables
            ])
            query = f"""
                WITH combined AS (
                    {union_sql}
                )
                SELECT a.filename, b.filename, a.checksum, a.filesize, b.filesize
                FROM combined a
                JOIN combined b
                ON a.checksum = b.checksum
                AND a.filename < b.filename
                AND a.filesize != b.filesize
                ORDER BY a.checksum, a.filename
            """
        else:
            query = """
                SELECT a.filename, b.filename, a.checksum, a.filesize, b.filesize
                FROM logs a
                JOIN logs b
                ON a.checksum = b.checksum
                AND a.filename < b.filename
                AND a.filesize != b.filesize
                WHERE a.checksum IS NOT NULL
                ORDER BY a.checksum, a.filename
            """

        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Database error in collision detection: {type(e).__name__} : {e}")
        return []


# 11/28/2025
def detect_copy(filename, inode, checksum, cursor, ps):
    if ps:
        query = '''
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

    for row in candidates:

        _, o_inode = row
        #     if o_filename != filename or o_inode != inode:
        #         return True
        if o_inode != inode:
            return True
    return False


def get_recent_changes(filename, cursor, table, e_cols=None):
    columns = [
        "timestamp", "filename", "changetime", "inode",
        "accesstime", "checksum", "entropy", "mime_id",
        "filesize", "symlink", "owner", "`group`",
        "permissions", "casmod", "target",
        "mtime_us"
    ]
    if e_cols:
        if isinstance(e_cols, str):
            e_cols = [col.strip() for col in e_cols.split(',') if col.strip()]
        columns += e_cols

    col_str = ", ".join(columns)

    query = f'''
        SELECT {col_str}
        FROM {table}
        WHERE filename = ?
        ORDER BY timestamp DESC
        LIMIT 1
    '''
    cursor.execute(query, (filename,))
    return cursor.fetchone()


def getcount(curs):
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


def clear_conn(conn, cur):
    # if cur and conn is None:
    #     print("Warning: cursor exists with no connection")
    for obj, name in ((cur, "cursor"), (conn, "connection")):
        try:
            if obj:
                obj.close()
        except Exception as e:
            print(f"Warning: failed to close {name}: {e}")


def increment_f(conn, c, records):
    if not records:
        return False

    inserted_entry = []

    for record in records:
        try:
            c.execute("""
                INSERT OR IGNORE INTO sys (
                    timestamp, filename, changetime, inode, accesstime, checksum,
                    entropy, mime_id, filesize, symlink, owner, `group`,
                    permissions, casmod, target, lastmodified, count,
                    mtime_us
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, record)

            if c.rowcount > 0:
                inserted_entry.append(record[1])

        except Exception as e:
            conn.rollback()
            print(f"Error while insert sys records skipping was unable to complete and then update count. increment_f {type(e).__name__} : {e}  \n{traceback.format_exc()}")
            return False

    for filename in inserted_entry:
        c.execute("UPDATE sys SET count = count + 1 WHERE filename = ?", (filename,))

    conn.commit()
    return True


def get_mime_map(cur):

    mime_to_info = {}
    id_to_info = {}
    cur.execute("SELECT id, mime, mime_primary, mime_subtype FROM mime_types")

    for row in cur:
        info = {
            "id": row[0],
            "mime": row[1],
            "primary": row[2],
            "subtype": row[3],
        }

        mime_to_info[row[1]] = info
        id_to_info[row[0]] = info

    return mime_to_info, id_to_info


def insert_mimes(cur, new_mime_rows):
    if not new_mime_rows:
        return
    cur.executemany(
        "INSERT INTO mime_types (id, mime, mime_primary, mime_subtype) VALUES (?, ?, ?, ?)",
        new_mime_rows
    )


def collision_check(xdata, cerr, c, ps):
    reported = set()
    csum = False
    colcheck = collision(c, ps)

    if colcheck:

        collision_map = defaultdict(set)
        for a_filename, b_filename, file_hash, size_a, size_b in colcheck:
            collision_map[a_filename, file_hash].add((b_filename, file_hash, size_a, size_b))
            collision_map[b_filename, file_hash].add((a_filename, file_hash, size_b, size_a))
        try:
            with open(cerr, "a", encoding="utf-8") as f:
                for record in xdata:
                    filename = record[1]
                    checks = record[5]
                    size_non_zero = record[8]
                    if size_non_zero:
                        key = (filename, checks)
                        if key in collision_map:
                            for other_file, file_hash, size1, size2 in collision_map[key]:
                                pair = tuple(sorted([filename, other_file]))
                                if pair not in reported:
                                    csum = True
                                    print(f"COLLISION: {filename} {size1} vs {other_file} {size2} | Hash: {file_hash}", file=f)
                                    reported.add(pair)
        except IOError as e:
            print(f"Failed to write collisions: {e} {type(e).__name__}  \n{traceback.format_exc()}")
    return csum


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
    except (TypeError, ValueError):
        return None


def parse_datetime(value, fmt="%Y-%m-%d %H:%M:%S"):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(str(value).strip(), fmt)
        # return dt.strftime(fmt)
    except (ValueError, TypeError, AttributeError):
        return None

# encoding
# 01/09/2025


# used for txt output so doesnt break on newlines
def escf_py(filename):
    filename = filename.replace('\n', '\\\\n')
    return filename
# def escf_py(filename):
    # filename = filename.replace('\\', '\\ap5c')
    # filename = filename.replace('\\', '\\\\')
    # filename = filename.replace('\n', '\\ap0A')
    # filename = filename.replace('"', '\\ap22')
    # filename = filename.replace('$', '\\$')
    # filename = filename.replace('\t', '\\t')
    # return filename


# not used here
def unescf_py(s):
    s = s.replace('\\ap0A', '\n')
    s = s.replace('\\ap22', '"')
    s = s.replace('\\ap5c', '\\')
    # s = s.replace('\\\\', '\\')
    # s = s.replace('\\$', '$')
    # s = s.replace('\\t', '\t')
    return s


# used in bash to allow for parsing in bash ha and arrives in  this format.
def ap_encode(filename):
    filename = filename.replace('\\', '\\ap5c')
    filename = filename.replace('\n', '\\ap0A')
    filename = filename.replace('"', '\\ap22')
    filename = filename.replace('\t', '\\ap09')
    # filename = filename.replace('$', '\\ap24')
    filename = filename.replace(' ', '\\ap20')
    return filename


# 12/22/2025 used to decode bash input. default used during parsing
def ap_decode(s):
    s = s.replace('\\ap0A', '\n')
    s = s.replace('\\ap09', '\t')
    s = s.replace('\\ap22', '"')
    # s = s.replace('\\ap24', '$')
    s = s.replace('\\ap20', ' ')
    s = s.replace('\\ap5c', '\\')
    return s


# not used in python backend. decode from the bash but leave newline escaped
def ap_dbdecode(s):
    s = s.replace('\\ap0A', '\\n')
    s = s.replace('\\ap09', '\t')
    s = s.replace('\\ap22', '"')
    # s = s.replace('\\ap24', '$')
    s = s.replace('\\ap20', ' ')
    s = s.replace('\\ap5c', '\\')
    return s

# end encoding


def to_bool(val):
    return val.lower() == "true" if isinstance(val, str) else bool(val)


# return filenm
def getnm(locale, ext=''):
    root = os.path.basename(locale)
    root, _ = os.path.splitext(root)
    return root + ext


# ha funcs
def get_md5(file_path):
    try:
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def calculate_checksum(file_path):
    try:
        hash_func = hashlib.md5()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception:
        return None


def sys_record_flds(record, sys_records, prev_count):
    sys_records.append((
        record[0],  # timestamp
        record[1],  # filename
        record[2],  # changetime
        record[3],  # inode
        record[4],  # accesstime
        record[5],  # checksum
        record[6],  # entropy
        record[7],  # mime_id
        record[8],  # filesize
        record[9],  # symlink
        record[10],  # owner
        record[11],  # group
        record[12],  # permissions
        record[13],  # casmod
        record[14],  # target
        record[15],  # lastmodified
        prev_count,  # incremented count or hardlink column
        record[17]   # mtime_us
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
        record[0] != metadata[0] or  # onr
        record[1] != metadata[1] or  # grp
        record[2] != metadata[2]  # perm
    )


# pstsrg
def goahead(filepath):
    try:
        st = filepath.stat()
        return st
    except FileNotFoundError:
        return "Nosuchfile"
    except (PermissionError, OSError, Exception):
        pass
        # print(f"Skipping {filepath.name}: {type(e).__name__} - {e}")
    return None


# if it is just a file we know the gpg would roughly be half the size. Final compLVL limit is based off of final comp size
def intst(target_file, compLVL):
    CSZE = 1024*1024
    if os.path.isfile(target_file):
        _, ext = os.path.splitext(target_file)
        try:
            file_size = os.stat(target_file).st_size
            size = file_size
            if ext != ".gpg":
                size = file_size // 2

            return size // CSZE >= compLVL  # no compression
        except Exception as e:
            print(f"Error setting compression of {target_file}: {e}")
    return False


def removefile(fpath):
    try:
        if os.path.isfile(fpath):
            os.remove(fpath)
            return True
    except (TypeError, FileNotFoundError):
        pass
    except Exception:
        pass
    return False


def update_config(config_file, setting_name, old_value, quiet=False):

    script_path = "/usr/local/save-changesnew/updateconfig.sh"
    cmd = [
        script_path,
        str(config_file),
        setting_name,
        old_value
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        if not quiet:
            print(result)
    else:
        print(result)
        print(f'Bash script failed {script_path}. error code: {result.returncode}')


def convert_mime_to_int(xdata: tuple, mime_hashmap: dict, id_to_mime: dict, next_mime_id: int = None, new_mime_rows: list | None = None, ) -> tuple[list, list, int]:
    """ convert tuple from mime str to int from hashmap
        update mime hashmap and id_to_mime hashmap and
        generate insertion list of unseen mime types
        for db """

    if not new_mime_rows:
        new_mime_rows = []  # for updating mime_types tbl and maintaining the index of mimes
    if not next_mime_id:
        next_mime_id = max(id_to_mime.keys(), default=0) + 1

    parsed_revised = []  # convert the mime field which is a str to an id
    for row in xdata:
        mime = row[7]

        if mime:
            if mime in mime_hashmap:
                mime_id = mime_hashmap[mime]["id"]
            else:
                mime_id = next_mime_id
                primary = subtype = None
                if "/" in mime:
                    primary, subtype = mime.split("/", 1)

                info = {
                    "id": next_mime_id,
                    "mime": mime,
                    "mime_primary": primary,
                    "mime_subtype": subtype

                }

                mime_hashmap[mime] = info
                id_to_mime[next_mime_id] = info

                new_mime_rows.append(
                    (mime_id, mime, primary, subtype)
                )

                next_mime_id += 1

            parsed_revised.append(
                row[:7] + (mime_id,) + row[8:]
            )
        else:
            parsed_revised.append(row)

    return parsed_revised, new_mime_rows, next_mime_id
