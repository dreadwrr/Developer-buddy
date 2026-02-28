import os


def get_base_folders(base_dir, EXCLDIRS_FULLPATH):
    c = 0
    base_folders = []
    if os.path.isdir(base_dir):
        c += 1
        base_folders.append(base_dir)
    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        if folder_path in EXCLDIRS_FULLPATH:
            continue
        if os.path.isdir(folder_path):
            c += 1
            base_folders.append(folder_path)
    return base_folders, c
