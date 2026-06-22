import os
# 06/21/2026

# Globals
MOUNT_FOLDERS = ("mnt",  "media")  # list any other base mount folders here. these could have files or files in folders that are not mount points
# for mounts in /var /home ect find those because -xdev wont. and are relavent folders for a search
MOUNTS_INCLUDE = ("/var", "/home", "/usr")


# from original design
# def get_dir_mtime(dirpath, locale):
#     try:
#         modified_ep = None
#         modified_time_str = None
#         st = os.lstat(dirpath)  # os.stat(file_path, follow_symlinks=False)
#         if st:
#             modified_ep = st.st_mtime
#             modified_time_str = epoch_to_str(modified_ep)
#         return modified_time_str, modified_ep, st
#     except Exception as e:
#         logging.debug(f"get_dir_mtime from {locale} access denied indexing directory on {dirpath}: {e}")
#         return None, None, None


# see MOUNTS_INCLUDE for relavent mount folders like /var /usr /home


def get_relavant_mounts(exclDIRS_fullpath):
    """ used by find -xdev to cover common mounts like /home or /var/lib/containers that it would miss """

    # first attempt but mounts in aufs doesnt parse correctly
    # import subprocess
    # result = subprocess.run(
    #     ["findmnt", "-rn", "-o", "TARGET"],
    #     capture_output=True,
    #     text=True,
    #     check=True,
    # )
    # sort so any base comes firsts
    # targets = sorted(result.stdout.splitlines(), key=len)

    # alternative to final method used with subprocess
    # result = subprocess.run(
    #     ['awk', '{print $4}', '/proc/self/mountinfo'],
    #     capture_output=True, text=True
    # )
    # targets = [
    #     line for line in result.stdout.splitlines()
    #     if line.startswith(prefixes)
    # ]
    # sort so any base comes firsts
    # targets.sort(key=len)

    # final method

    # find any mounts we are interested in
    targets = []
    with open('/proc/self/mountinfo') as f:

        # sort so any base comes firsts
        targets = sorted(
            (line.split()[3] for line in f
                if line.split()[3].startswith(MOUNTS_INCLUDE)),
            key=len
        )

    # list any tmpfs mounted on /
    # for d in /*; do
    #     printf '%-15s ' "$d"
    #     df -T "$d" | awk 'NR==2 {print $2, $7}'
    # done
    # and include any other in mounts

    mounts = []
    # find any mounts such as /home /var /usr from MOUNTS_INCLUDE
    for t in targets:
        if not any(t == p or t.startswith(p + "/") for p in MOUNTS_INCLUDE):
            continue
        if t in exclDIRS_fullpath:
            continue
        # skip if already an existing parent
        if any(t.startswith(m + "/") or t == m for m in mounts):
            continue

        mounts.append(t)
    return mounts


def check_mount_folders(folder_path, exclDIRS_fullpath):
    """ instead of excluding mount areas such as mnt and media by default only exclude if specifically in config exclDIRS
        exclude only those that dont belong to the device. this way if there are any files or files in folders they are
        included in files_search python,  find_created and index_system.

        add to exclDIRS_fullpath the mount points to exclude

        """
    x = 0
    mnt_dev = os.stat(folder_path).st_dev

    for entry in os.scandir(folder_path):
        if entry.is_dir():
            if entry.path in exclDIRS_fullpath:
                continue
            dev = os.stat(entry.path).st_dev

            if dev != mnt_dev:
                x += 1
                exclDIRS_fullpath.append(entry.path)
    return x


# see MOUNT_FOLDERS to look for mounts to exclude


def get_mount_excludes(basedir, exclDIRS_fullpath, as_set=False) -> list | set:
    """ get the mount points to exclude from MOUNT_FOLDERS
         for use by index_system in dirwalker """

    mount_folders = (os.path.join(basedir, fld) for fld in MOUNT_FOLDERS)
    for fld in mount_folders:
        if os.path.exists(fld):
            check_mount_folders(fld, exclDIRS_fullpath)
    if not as_set:
        return exclDIRS_fullpath
    return set(exclDIRS_fullpath)


def get_base_folders(basedir, exclDIRS_fullpath):
    """ used to get the search areas for find_created and also to display the searched folders for recentchanges search """

    c = 0
    base_folders = []
    if os.path.isdir(basedir):
        c += 1
        base_folders.append(basedir)

    # original
    # for folder_name in os.listdir(basedir):
    #     folder_path = os.path.join(basedir, folder_name)
    #     if folder_path in exclDIRS_fullpath
    #         continue
    #     if os.path.isdir(folder_path):
    #         c += 1
    #         base_folders.append(folder_path)

    for entry in os.scandir(basedir):
        if entry.is_dir():

            path = entry.path
            # name = entry.name

            if path in exclDIRS_fullpath:
                continue
            c += 1
            base_folders.append(path)

    return base_folders, c
