import csv
import fnmatch
import hashlib
import logging
import os
import pwd
import re
import shutil
import sys
import tomllib
import traceback
from io import StringIO
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# terminal and hardlink suppression.  regex

suppress_terminal = [
    r'mozilla',
    r'\.mozilla',
    r'chromium-ungoogled',
    r'/home/{{user}}/\.cache/somefolder',
    # r'google-chrome',
    # uncomment if needed
]


# Cache clear

# Cache clear patterns to delete from db
cache_clear = [
    "%caches%",
    "%cache2%",
    "%Cache2%",
    "%.cache%",
    "%share/Trash%",
    f"%home/{{user}}/.local/state/wireplumber%",
    "%root/.local/state/wireplumber%",
    "%usr/share/mime/application%",
    "%usr/share/mime/text%",
    "%usr/share/mime/image%",
    "%release/cache%",
]


# filter hits to reset on cache clear. copy literal items from /usr/local/save-changesnew/filter.py to. resets to 0
flth_literal_patterns = [
    r'/home/{user}/\.Xauthority',
    r'/root/\.Xauthority',
    r'/home/{user}/\.local/state/wireplumber',
    r'/root/\.local/state/wireplumber'
]

# end Cache clear


def sbwr(escaped_user):
    suppress_list = [p.replace("{{user}}", escaped_user) for p in suppress_terminal]
    compiled = [re.compile(p) for p in suppress_list]
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


def collision(cursor, is_sys):
    try:
        if is_sys:
            tables = ['logs', 'sys']
            union_sql = " UNION ALL ".join([
                f"SELECT filename, checksum, filesize FROM {t} WHERE checksum IS NOT NULL and symlink is NULL" for t in tables
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
                    AND a.symlink IS NULL
                    AND b.symlink IS NULL
                ORDER BY a.checksum, a.filename
            """

        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Database error in collision detection: {type(e).__name__} : {e}")
        return []


# 12/15/2025
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
    # for o_filename, o_inode in candidates:
    #     if o_filename != filename or o_inode != inode:
    #         return True
    for _, o_inode in candidates:
        if o_inode != inode:
            return True

    return None


def get_recent_changes(filename, cursor, table, e_cols=None):
    columns = [
        "timestamp", "filename", "changetime", "inode",
        "accesstime", "checksum", "filesize", "owner",
        "`group`", "permissions", "symlink", "casmod"
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


def increment_f(conn, c, records):
    if not records:
        return False

    inserted_entry = []

    for record in records:
        try:
            c.execute("""
                INSERT OR IGNORE INTO sys (
                    timestamp, filename, changetime, inode, accesstime, checksum,
                    filesize, symlink, owner, `group`, permissions, casmod, lastmodified, count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def ccheck(xdata, cerr, c, ps):
    reported = set()

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
                    csum = record[5]
                    size_non_zero = record[6]
                    sym = record[7]
                    if sym != 'y' and size_non_zero:
                        key = (filename, csum)
                        if key in collision_map:
                            for other_file, file_hash, size1, size2 in collision_map[key]:
                                pair = tuple(sorted([filename, other_file]))
                                if pair not in reported:
                                    print(f"COLLISION: {filename} {size1} vs {other_file} {size2} | Hash: {file_hash}", file=f)
                                    reported.add(pair)
        except IOError as e:
            print(f"Failed to write collisions: {e} {type(e).__name__}  \n{traceback.format_exc()}")


# Convert SQL-like % wildcard to fnmatch *
def matches_any_pattern(s, patterns):

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


# obj from obj or str
def parse_datetime(value, fmt="%Y-%m-%d %H:%M:%S"):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(str(value).strip(), fmt)
        # return dt.strftime(fmt)
    except (ValueError, TypeError, AttributeError):
        return None


def ap_decode(s):
    s = s.replace('\\ap0A', '\n')
    s = s.replace('\\ap09', '\t')
    s = s.replace('\\ap22', '"')
    # s = s.replace('\\ap24', '$')
    s = s.replace('\\ap20', ' ')
    s = s.replace('\\ap5c', '\\')
    return s


def escf_py(filename):
    filename = filename.replace('\\', '\\ap5c')
    filename = filename.replace('\n', '\\\\n')
    # filename = filename.replace('"', '\\"')
    # filename = filename.replace('\t', '\\t')
    # filename = filename.replace('$', '\\$')
    return filename


def unescf_py(s):
    s = s.replace('\\\\n', '\n')
    # s = s.replace('\\"', '"')
    # s = s.replace('\\t', '\t')
    # s = s.replace('\\$', '$')
    s = s.replace('\\ap5c', '\\')
    return s


# ha funcs
def get_md5(file_path):
    try:
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except FileNotFoundError:
        return None
    except Exception:
        # print(f"Error reading {file_path}: {e}")
        return None


def is_integer(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def is_valid_datetime(value, fmt):
    try:
        datetime.strptime(str(value).strip(), fmt)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def getstdate(st, fmt):
    a_mod = int(st.st_mtime)
    afrm_str = datetime.fromtimestamp(a_mod).strftime(fmt)  # datetime.utcfromtimestamp(a_mod).strftime(fmt)
    afrm_dt = parse_datetime(afrm_str, fmt)
    return afrm_dt, afrm_str


def new_meta(record, metadata):
    return (
        record[0] != metadata[0] or  # onr
        record[1] != metadata[1] or  # grp
        record[2] != metadata[2]  # perm
    )


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
        record[10],  # permissions
        record[11],  # casmod
        record[12],  # lastmodified
        prev_count  # count
    ))


# hanly mc
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


# prepare for file output
def dict_to_list_sys(cachedata):
    data_to_write = []
    for root, versions in cachedata.items():
        for modified_ep, metadata in versions.items():
            row = {
                "checksum": metadata.get("checksum") or '',
                "size": '' if metadata.get("size") is None else metadata["size"],
                "modified_time": metadata.get("modified_time") or '',
                "modified_ep": '' if modified_ep is None else modified_ep,
                # "user": metadata.get("user"),
                # "group": metadata.get("group"),
                "root": root,
            }
            data_to_write.append(row)
    return data_to_write


# recentchangessearch
def dict_string(data: list[dict]) -> str:
    if not data:
        return ""

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys(), delimiter='|', quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def load_config(conf_path):

    if not conf_path.is_file():
        print("Unable to find config file:", conf_path)
        sys.exit(1)

    try:
        with open(conf_path, 'rb') as f:
            config = tomllib.load(f)
    except Exception as e:
        print(f"Failed to parse TOML: {e}")
        sys.exit(1)

    return config


# user configuration location
def lcl_config(user, appdata_local=None):

    home_dir = None
    config_file = "config - Copy.toml"

    if appdata_local:
        default_conf = appdata_local / "config" / config_file
    else:
        default_conf = Path("/usr/local/save-changesnew/config/" + config_file)

    try:
        user_info = pwd.getpwnam(user)
        home_dir = Path(user_info.pw_dir)

        uid = user_info.pw_uid
        gid = user_info.pw_gid
        # uid = pwd.getpwnam(USR).pw_uid  # user doesnt exist KeyError **
        # gid = grp.getgrnam(user).gr_gid

    except KeyError:
        raise ValueError(f"Invalid user: {user}")

    xdg_env = os.environ.get("XDG_CONFIG_HOME")
    xdg = Path(xdg_env) if xdg_env else None

    if xdg:
        config_home = xdg
    elif home_dir:
        config_home = home_dir / ".config"
    else:
        if user == "root":
            default_conf_home = "/root/.config"
        else:
            default_conf_home = f"/home/{user}/.config"
        config_home = Path(default_conf_home)

    config_local = config_home / "save-changesnew"
    toml_file = config_local / "config.toml"

    if not toml_file.is_file():
        if not default_conf.is_file():
            raise ValueError(f"No default configuration found at {default_conf}. config.toml")

        os.makedirs(config_local, mode=0o755, exist_ok=True)
        shutil.copy(default_conf, toml_file)

    if toml_file.is_file():
        return toml_file, home_dir, uid, gid

    raise FileNotFoundError(f"Unable to find config.toml config file in {config_local}")


# app location
def get_wdir():
    # wdir = Path(sys.argv[0]).resolve().parent  # calling script
    # wdir = Path(__file__).resolve().parent.parent  # if files are moved to a src or seperate directory its the one below it
    wdir = Path(__file__).resolve().parent
    return wdir


def set_logger(root, process_label="MAIN"):
    fmt = logging.Formatter(f'%(asctime)s [%(levelname)s] [{process_label}] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    for handler in root.handlers:
        handler.setFormatter(fmt)


# Before setup_logger - return handler for user setting
def init_logger(ll_level, appdata_local):
    log_flnm = "errs.log"
    level_map = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "DEBUG": logging.DEBUG,
    }
    log_level = level_map.get(ll_level, logging.ERROR)
    log_path = appdata_local / "logs" / log_flnm

    return log_path, log_level


# set log level by handler for script or script area
def setup_logger(ll_level=None, process_label="MAIN", wdir=None):
    root = logging.getLogger()
    try:
        if not wdir:
            wdir = Path(get_wdir())  # appdata software install aka workdir

        if wdir and not ll_level:
            config_path = Path(wdir) / "config" / "config.toml"

            config = load_config(config_path)
            ll_level = config['search'].get('logLEVEL', 'ERROR')

        if wdir and ll_level:
            appdata_local = wdir

            if not root.hasHandlers():

                log_path, log_level = init_logger(ll_level.upper(), appdata_local)

                logging.basicConfig(
                    filename=log_path,
                    level=log_level,
                    format=f'%(asctime)s [%(levelname)s] [%(name)s] [{process_label}] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            else:
                set_logger(root, process_label)
        else:
            print("Unable to get app location to set logging or log level")
    except Exception as e:
        print(f"Error setting up logger: {type(e).__name__} {e} \n{traceback.format_exc()}")
