import os
import re
import multiprocessing
from collections import defaultdict

def sbwr(LCLMODULENAME):
    return [
        'mozilla',
        '.mozilla',
        'chromium-ungoogled',
        # 'google-chrome',
        LCLMODULENAME
    ]

def count_inodes_for_dirs(directories):
    inode_map = defaultdict(int)
    dirs_str = " ".join(directories)
    for inode in os.popen(f'find {dirs_str} -xdev -printf "%i\n" 2>/dev/null'):
        inode_map[inode.strip()] += 1
    return inode_map

def ulink(input_array, LCLMODULENAME, supbrwr):
    webb = sbwr(LCLMODULENAME)
    inode_map = defaultdict(int)
    inodes_array = []

    # Step 1: extract inode or mark None
    for line in input_array:
        ck = False
        cFILE = line[1]
        inode = None

        if cFILE:

            inode_candidate = line[4]

            if supbrwr == "true":
                if any(item and re.search(item, cFILE) for item in webb):
                    ck = True

            if not ck:
                inode = inode_candidate

        if inode is None or ck:
            inodes_array.append(None)
        else:
            inodes_array.append(inode)

    # Step 2: count inodes system-wide
    chunks = [
        ['/bin', '/etc', '/home'],
        ['/lib', '/lib64', '/opt'],
        ['/root', '/sbin', '/usr', '/var']
    ]

    with multiprocessing.Pool(processes=3) as pool:
        results = pool.map(count_inodes_for_dirs, chunks)

    for result in results:
        for inode, count in result.items():
            inode_map[inode] += count

    # Step 3: assign counts (None if ≤1)
    counts_result = []
    for inode in inodes_array:
        if inode is None:
            counts_result.append("None")
        else:
            count = inode_map.get(inode, 0)
            if count <= 1:
                counts_result.append("None")
            else:
                counts_result.append(str(count))

    output_array = [
        " ".join(map(str, line)) + " " + count
        for line, count in zip(input_array, counts_result)
    ]

    return output_array