import logging
import sqlite3
from pyfunctions import escf_py
from pysql import detect_copy
from pysql import increment_f
SENTINEL = None
""" Old way using a thread """


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
            results, sys_records = item

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

# singecore
# work_q = queue.SimpleQueue()
# work_q.put((all_results, batch_incr))
# work_q.put(SENTINEL)
# logger_process(work_q, rout, scr, cerr, dbopt, ps, logger)
# mc
# work_q = mp.Queue(maxsize=64)
# t = threading.Thread(
#     target=logger_process,
#     args=(work_q, rout, scr, cerr, dbopt, ps, logger),
#     daemon=True,
# )
# t.start()

# work_q.put(SENTINEL)
# t.join()
# work_q.close()
# work_q.join_thread()
