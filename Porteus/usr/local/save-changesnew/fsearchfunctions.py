# 02/26/2026


def upt_cache(cfr, checks, file_size, time_stamp, modified_ep, file_path):

    if not checks:
        return
    versions = cfr.setdefault(file_path, {})
    row = versions.get(modified_ep)

    if row and row.get("checksum") == checks and row.get("size") == file_size:
        return

    cfr[file_path][modified_ep] = {
        "checksum": checks,
        "size": file_size,
        "modified_time": time_stamp,
    }
    # "owner": str(owner) if owner else '',
    # "group": str(group) if group else ''


def get_cached(cfr, file_size, modified_ep, file_path):
    if not isinstance(cfr, dict):
        return None

    versions = cfr.get(file_path)
    if not versions:
        return None

    if modified_ep is not None:
        row = versions.get(modified_ep)
        if row:
            row_size = row.get("size")
            if (
                row_size is not None
                and file_size == row["size"]
                and row.get("checksum")
            ):
                return {
                    "checksum": row.get("checksum"),
                    "modified_ep": modified_ep
                }
            # "user": row.get("owner"),
            # "group": row.get("group"),

    return None


# return the last known modified_ep
def get_last_mtime(cfr, file_path, latest_ep):
    if not isinstance(cfr, dict):
        return None

    versions = cfr.get(file_path)
    if not isinstance(versions, dict) or not versions:
        return None

    candidates = [ep for ep in versions.keys() if ep not in (None, '', latest_ep)]
    if not candidates:
        return None

    return max(candidates)


def normalize_timestamp(mod_time: str) -> int:
    sec, frac = mod_time.split(".")
    frac = (frac + "000000")[:6]
    return int(sec) * 1_000_000 + int(frac)
