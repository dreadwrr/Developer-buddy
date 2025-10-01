import os
import re
import multiprocessing
import subprocess
from collections import defaultdict
from pyfunctions import sbwr

def count_inodes_for_dirs(directories):
    inode_map = defaultdict(int)
    try:
        result = subprocess.run(
            ['find'] + directories+ ['-xdev', '-printf', '%i\n'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True
        )
        for inode in result.stdout.splitlines():
            inode_map[inode.strip()] += 1
    except Exception as e:
        print(f"Error running find: {e}")
    return inode_map

def ulink(input_array, LCLMODULENAME, supbrwr):
    webb = sbwr(LCLMODULENAME)
    inode_map = defaultdict(int)
    inodes_array = []

    for line in input_array:
        ck = False
        cFILE = line[1]
        inode = None

        if cFILE:

            inode_candidate = line[3]

            ck = supbrwr and any(item and re.search(item, cFILE) for item in webb)

            if not ck:
                inode = inode_candidate

        if inode is None or ck:
            inodes_array.append(None)
        else:
            inodes_array.append(inode)

    chunks = [
        [d for d in group if os.path.exists(d)]
        for group in [
            ['/bin', '/etc', '/home'],
            ['/lib', '/lib64', '/opt'],
            ['/root', '/sbin', '/usr', '/var']
        ]
    ]

    with multiprocessing.Pool(processes=3) as pool:
        results = pool.map(count_inodes_for_dirs, chunks)

    for result in results:
        for inode, count in result.items():
            inode_map[inode] += count


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
        line[:13] + (str(count),) + line[14:]
        for line, count in zip(input_array, counts_result)
    ]

#output_array = [line[:-1] + (str(count),) for line, count in zip(input_array, counts_result)]  Append at end


    return output_array