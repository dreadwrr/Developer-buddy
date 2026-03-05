import logging
import multiprocessing as mp
import os
import queue
import traceback
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from fsearch import process_line_worker
from fsearchfunctions import upt_cache
from logs import emit_log
from logs import init_process_worker
from logs import logs_to_queue
from logs import logging_worker


def process_lines(lines, file_type, table, search_start_dt, process_label, user_setting, logging_values, CACHE_F):

    mMODE = user_setting['mMODE']
    checksum = user_setting['checksum']

    ck_results = []

    logger = logging.getLogger(process_label)
    len_lines = len(lines)

    if len_lines < 80 or mMODE.lower() != "mc":

        log_q = queue.SimpleQueue()
        init_process_worker(log_q)

        try:

            tlog = threading.Thread(target=logging_worker, args=(log_q, logger), daemon=True)
            tlog.start()

            ck_results, log_ = process_line_worker(lines, checksum, file_type, table, search_start_dt, CACHE_F)
            if log_:
                logs_to_queue(log_, log_q)
        finally:
            log_q.put(None)
            tlog.join()
    else:

        # min_chunk_size = 10
        # max_workers = max(1, min(8, os.cpu_count() or 4, len(lines) // min_chunk_size))
        max_workers = min(8, os.cpu_count() or 1, len_lines)
        chunk_size = max(1, (len_lines + max_workers - 1) // max_workers)
        chunks = [lines[i:i + chunk_size] for i in range(0, len_lines, chunk_size)]

        ctx = mp.get_context()
        log_q = ctx.Queue(maxsize=4096)
        log_t = threading.Thread(target=logging_worker, args=(log_q, logger), daemon=True)
        log_t.start()

        try:
            with ProcessPoolExecutor(
                max_workers=max_workers,
                mp_context=ctx,
                initializer=init_process_worker,
                initargs=(log_q,)
            ) as executor:
                futures = [
                    executor.submit(
                        process_line_worker, chunk, checksum, file_type, table, search_start_dt, CACHE_F

                    )
                    for idx, chunk in enumerate(chunks)
                ]
                for future in as_completed(futures):
                    try:
                        results, log_ = future.result()
                        if results:
                            ck_results.extend(results)
                        if log_:
                            logs_to_queue(log_, log_q)

                    except BrokenProcessPool as e:
                        print("fsearch failed in mc")
                        emit_log("ERROR", f"fsearch error {e} \n{traceback.format_exc()}", log_q)
                        for f in futures:
                            f.cancel()
                        break
                    except Exception as e:
                        emsg = f"Worker error occurred: {type(e).__name__} : {e} \n{traceback.format_exc()}"
                        print(emsg)
                        emit_log("ERROR", emsg, log_q)
        finally:
            log_q.put(None)
            log_t.join()
            log_q.close()
            log_q.join_thread()

    results = [item for item in ck_results if item is not None]  # results = [item for sublist in ck_results if sublist is not None for item in sublist]  # flatten the list

    sortcomplete = []
    complete = []
    cwrite = []

    for res in results:
        if res is None or not res:
            continue
        if isinstance(res, tuple) and len(res) > 3:
            if res[0] == "Nosuchfile" or res[0] == "Deleted":
                complete.append((res[0], res[1], res[2], res[3]))
            elif res[0] == "Cwrite":
                cwrite.append(res[1:])
                sortcomplete.append(res[1:])
            else:
                sortcomplete.append(res[1:])
    try:

        if table != "sys" and cwrite:

            for res in cwrite:
                time_stamp = res[0].strftime("%Y-%m-%d %H:%M:%S")
                # file_path = res[1]
                checks = res[5]
                file_size = res[6]
                # user = res[8]
                # group = res[9]
                mtime_epoch = res[15]
                epath = res[16]
                upt_cache(CACHE_F, checks, file_size, time_stamp, mtime_epoch, epath)

    except Exception as e:
        msg = f'Error updating cache: {type(e).__name__}: {e}'
        print(msg)
        logger.error(msg, exc_info=True)

    return sortcomplete, complete
#
# End parallel #
