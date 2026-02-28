import gc
import logging
import traceback
import multiprocessing as mp
import os
import queue
import sqlite3
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from hanlymc import hanly
from logs import write_logs_to_logger
from pyfunctions import cprint
from pyfunctions import escf_py
from pysql import detect_copy
from pysql import increment_f
# 02/26/2026

SENTINEL = None


# tfile
def logger_process(queue, rout, scr, cerr, dbopt, ps, logger=None):
    # append rout messages to the rout list from hanly
    # if there are sys_records add them to the database sys changes sys_b
    #
    # distribute the appropriate messages to cerr and scr.
    log = logger if logger else logging
    key_to_files = {
        "flag": [rout],
        "cerr": [cerr],
        "scr": [scr],
    }
    with sqlite3.connect(dbopt) as conn:
        c = conn.cursor()
        while True:
            item = queue.get()
            if item is SENTINEL:
                break
            results, sys_records, logs = item
            if logs:
                write_logs_to_logger(logs, log)

            file_messages = {}

            for entry in results:

                for key, files in key_to_files.items():
                    if key in entry:

                        messages = entry[key]
                        if not isinstance(messages, list):
                            messages = [messages]
                        for fpath in files:
                            if isinstance(fpath, list):  # rout is a list
                                fpath.extend(messages)
                            else:
                                file_messages.setdefault(fpath, []).extend(messages)  # write these to cerr scr

                if "dcp" in entry:
                    dcp_messages = entry["dcp"]
                    if not isinstance(dcp_messages, list):
                        dcp_messages = [dcp_messages]

                    if dcp_messages:

                        try:
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
                                            rout.append(f'Copy {timestamp} {ct} {label}')
                                else:
                                    log.debug("Skipping dcp message due to insufficient length: %s", msg)

                        except Exception as e:
                            em = "Error checking for copies"
                            print(f"{em} {e} {type(e).__name__}")
                            log.error(em, exc_info=True)

            # update sys changes in one batch
            if sys_records:
                try:
                    increment_f(conn, c, sys_records, log)  # add changes to sys_b
                except Exception as e:
                    em = "Failed to update sys table in hanlyparallel increment_f"  # {traceback.format_exc()}"
                    print(f"{em} : {e} {type(e).__name__}")
                    log.error(em, exc_info=True)

            for fpath, messages in file_messages.items():
                if messages:
                    try:
                        with open(fpath, "a", encoding="utf-8") as f:
                            f.write('\n'.join(str(msg) for msg in messages) + '\n')

                    except IOError as e:
                        em = f"Error logging to {fpath}"
                        print(f"{em}: {e}")
                        log.error(em, exc_info=True)
                    except Exception as e:
                        em = f"Unexpected error to {fpath} logger_process"
                        print(f"{em}: {e} : {type(e).__name__}")
                        log.error(em, exc_info=True)


def hanly_parallel(rout, scr, cerr, mMODE, parsed, ANALYTICSECT, checksum, cdiag, dbopt, ps, user, logging_values):

    all_results = []
    batch_incr = []
    if not parsed:
        return
    len_parsed = len(parsed)
    if len_parsed == 0:
        return
    csum = False

    if ANALYTICSECT:
        cprint.green('Hybrid analysis on')

    logger = logging.getLogger("HANLY")

    if len_parsed < 80 or mMODE == "default":

        all_results, batch_incr, logs, csum = hanly(parsed, checksum, cdiag, dbopt, ps, user, logging_values)
        work_q = queue.SimpleQueue()
        work_q.put((all_results, batch_incr, logs))
        work_q.put(SENTINEL)
        logger_process(work_q, rout, scr, cerr, dbopt, ps, logger)
    else:
        max_workers = min(8, os.cpu_count() or 1, len_parsed)
        chunk_size = max(1, (len_parsed + max_workers - 1) // max_workers)
        chunks = [parsed[i:i + chunk_size] for i in range(0, len_parsed, chunk_size)]

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    hanly, chunk, checksum, cdiag, dbopt, ps, user, logging_values
                )
                for chunk in chunks
            ]
            work_q = mp.Queue(maxsize=64)
            t = threading.Thread(
                target=logger_process,
                args=(work_q, rout, scr, cerr, dbopt, ps, logger),
                daemon=True,
            )
            t.start()
            for future in as_completed(futures):
                try:
                    results, sys_records, logs, is_csum = future.result()
                    work_q.put((results, sys_records, logs))
                    if is_csum:
                        csum = True

                except BrokenProcessPool as e:
                    print("hanly encountered an error")
                    logger.error(f"unable to run hanly an error occured {e} \n{traceback.format_exc()}")
                    for f in futures:
                        f.cancel()
                    break
                except Exception as e:
                    em = f"Worker error from hanly multiprocessing: {type(e).__name__} {e} \n {traceback.format_exc()}"
                    print(em)
                    logger.error(em)
            work_q.put(SENTINEL)
            t.join()
            work_q.close()
            work_q.join_thread()
    print("processing results")
    gc.collect()
    return csum
