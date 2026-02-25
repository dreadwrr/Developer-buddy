import traceback
import os
import sqlite3
from concurrent.futures import ProcessPoolExecutor, as_completed
from hanlymc import hanly
from pyfunctions import detect_copy
from pyfunctions import GREEN, RESET
from pyfunctions import escf_py
from pyfunctions import increment_f
# 02/25/2025


def logger_process(results, sys_records, rout, scr, cerr, dbopt="/usr/local/save-changesnew/recent.db", ps=False):

    key_to_files = {
        "flag": [rout],
        "cerr": [cerr],
        "scr": [scr],
    }

    with sqlite3.connect(dbopt) as conn:
        c = conn.cursor()

        file_messages = {}
        for entry in results:
            for key, files in key_to_files.items():
                if key in entry:
                    messages = entry[key]
                    if not isinstance(messages, list):
                        messages = [messages]
                    for fpath in files:
                        file_messages.setdefault(fpath, []).extend(messages)

            if "dcp" in entry:
                dcp_messages = entry["dcp"]
                if not isinstance(dcp_messages, list):
                    dcp_messages = [dcp_messages]

                if dcp_messages:
                    try:
                        with open(rout, 'a') as file:
                            for msg in dcp_messages:
                                if msg is not None and len(msg) > 6:
                                    filesize = msg[6]
                                    if filesize:
                                        timestamp = msg[0]
                                        filepath = msg[1]
                                        ct = msg[2]
                                        inode = msg[3]
                                        checksum = msg[5]
                                        result = detect_copy(filepath, inode, checksum, c, ps)
                                        if result:
                                            label = escf_py(filepath)
                                            print(f'Copy {timestamp} {ct} {label}', file=file)

                    except Exception as e:
                        print(f"Error updating DB for sys entry '{msg}': {e} {type(e).__name__}")

        # Update the counts once in sys table
        if sys_records:
            try:
                increment_f(conn, c, sys_records)
            except Exception as e:
                print(f"Failed to update sys table in hanlyparallel increment_f : {e}  \n {traceback.format_exc()}")

    for fpath, messages in file_messages.items():
        if messages:
            try:

                with open(fpath, "a", encoding="utf-8") as f:
                    f.write('\n'.join(str(msg) for msg in messages) + '\n')

            except IOError as e:
                print(f"logger_process Error logger to {fpath}: as {e}")
            except Exception as e:
                print(f"Unexpected error to {fpath} logger_process: {e} : {type(e).__name__}")


def hanly_parallel(rout, scr, cerr, parsed, ANALYTICSECT, checksum, cdiag, dbopt, ps, turbo, user):

    all_results, batch_incr = [], []
    if not parsed:
        return
    len_parsed = len(parsed)
    if len_parsed == 0:
        return
    csum = False

    if ANALYTICSECT:
        print(f'{GREEN}Hybrid analysis on{RESET}')

    if len(parsed) < 80 or turbo != 'mc':
        all_results, batch_incr, csum = hanly(parsed, checksum, cdiag, dbopt, ps, user)
    else:
        max_workers = min(8, os.cpu_count() or 1, len_parsed)
        chunk_size = max(1, (len_parsed + max_workers - 1) // max_workers)
        chunks = [parsed[i:i + chunk_size] for i in range(0, len_parsed, chunk_size)]

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    hanly, chunk, checksum, cdiag, dbopt, ps, user
                )
                for chunk in chunks
            ]
            for future in as_completed(futures):
                try:
                    results, sys_records, is_csum = future.result()
                    if results:
                        all_results.extend(results)
                    if sys_records:
                        batch_incr.extend(sys_records)
                    if is_csum:
                        csum = True
                except Exception as e:
                    print(f"Worker error from hanly multiprocessing: {type(e).__name__} {e} \n {traceback.format_exc()}")

            # for future in futures:       original
            # 	try:
            # 		all_results.extend(future.result())
            # 	except Exception as e:
            # 		print(f"Worker error from hanly multiprocessing: {type(e).__name__} {e} \n {traceback.format_exc()}")
    print("processing results")
    logger_process(all_results, batch_incr, rout, scr, cerr, dbopt, ps)

    return csum
