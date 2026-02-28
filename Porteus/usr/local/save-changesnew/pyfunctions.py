import csv
import fnmatch
import hashlib
import re
from datetime import datetime
from configfunctions import not_absolute


# terminal and hardlink suppression.  regex

suppress_terminal = [
    r'mozilla',
    r'\.mozilla',
    r'chromium-ungoogled',
    r'/home/{{user}}/\.cache/somefolder',
    r'\.local/share/Trash'
    # r'google-chrome'
    # uncomment if needed
]


# Cache clear patterns to delete from db
cache_clear = [
    "%caches%",
    "%cache2%",
    "%Cache2%",
    "%.cache%",
    "%share/Trash%",
    "%home/{{user}}/.local/state/wireplumber%",
    "%root/.local/state/wireplumber%",
    "%usr/share/mime/application%",
    "%usr/share/mime/text%",
    "%usr/share/mime/image%",
    "%release/cache%",
]


# filter hits to reset on Cache clear. copy literal items from /usr/local/save-changesnew/filter.py to. resets to 0
flth_literal_patterns = [
    r'\.cache',
    r'/home/{{user}}/\.Xauthority',
    r'/root/\.Xauthority',
    r'\.local/share',
    r'/root/xauth',
    r'/var/cache',
    r'/var/log',
    r'/var/run',
    r'/usr/share/mime',
    r'\.gnupg',
    r'/root/\.xauth'
]


def suppress_list(escaped_user):
    suppress_list = [p.replace("{{user}}", escaped_user) for p in suppress_terminal]
    compiled = [re.compile(p) for p in suppress_list]
    return compiled


def get_delete_patterns(usr):
    patterns = [p.replace("{{user}}", usr) for p in cache_clear]
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


def user_path(settingName, theusr):

    if isinstance(settingName, list):
        processed = []
        if theusr == "root":
            for p in settingName:
                out = p
                if "{{user}}" in p and not p.startswith("{{user}}"):
                    _, end = p.split("{{user}}", 1)
                    out = "/{{user}}"
                    if not_absolute(p, quiet=True):
                        out = "{{user}}"
                    out = out + end
                processed.append(out)
        else:
            processed = settingName
        return [s.replace("{{user}}", theusr) for s in processed]
    elif isinstance(settingName, str):
        if theusr == "root":
            if "{{user}}" in settingName and not settingName.startswith("{{user}}"):
                _, end = settingName.split("{{user}}", 1)
                out = "/root"
                if not_absolute(settingName, quiet=True):
                    out = "root"
                return out + end
        return settingName.replace("{{user}}", theusr)
    else:
        raise ValueError(f"Invalid type for settingName: {type(settingName).__name__}, expected str or list")


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
        record[12],  # target
        record[13],  # lastmodified
        prev_count,  # count
        record[15]  # mtime_us
    ))
