import csv
import fnmatch
import hashlib
import re
from datetime import datetime
from configfunctions import not_absolute
from filter import _filterhitRESET


def suppress_list(escaped_user, suppress_list):
    compiled = [re.compile(re.escape(p)) for p in suppress_list]
    return compiled


def cache_clear_patterns(usr, cachermPATTERNS):
    return [
        f"%{p.replace("{{user}}", usr)}%"
        for p in cachermPATTERNS
    ]


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


def reset_csvliteral(csv_file):

    patterns_to_reset = _filterhitRESET
    is_diff = False
    try:
        with open(csv_file, newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
        for row in rows[1:]:
            if row[0] in patterns_to_reset:
                if row[1] != '0':
                    is_diff = True
                row[1] = '0'
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    except (FileNotFoundError, PermissionError):
        print(f"nfs permission error on {csv_file} reset_csvliteral.")
        pass
    return is_diff


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


def ap_encode(s):
    s = s.replace('\\', '\\ap5c')
    s = s.replace('\n', '\\ap0A')
    s = s.replace('"', '\\ap22')
    s = s.replace('\t', '\\ap09')
    # s = s.replace('\\ap24', '$')
    s = s.replace(' ', '\\ap20')
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


def date_from_stat(st, fmt):
    a_mod = st.st_mtime
    afrm_dt = datetime.fromtimestamp(a_mod)  # datetime.utcfromtimestamp(a_mod)
    afrm_str = afrm_dt.strftime(fmt)
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
        prev_count,  # count
        record[17]  # mtime_us
    ))


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
