import logging
import os
from pathlib import Path
from configfunctions import find_install


def filename_of_handler():
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.FileHandler):
            return Path(handler.baseFilename)
    return None
    # root = logging.getLogger()
    # for h in root.handlers:
    #     if isinstance(h, logging.FileHandler):
    #         log_path = Path(h.baseFilename)
    #         return log_path


def set_logger(root, process_label="MAIN", level=None):
    fmt = logging.Formatter(f'%(asctime)s [%(name)s] [{process_label}] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')  # [%(levelname)s]
    for handler in root.handlers:
        handler.setFormatter(fmt)
        if level is not None:
            handler.setLevel(level)


def set_log_level(log_file, level):
    level_map = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "DEBUG": logging.DEBUG,
    }
    log_level = level_map.get(level, logging.ERROR)
    return log_level


def set_format(log_file, level, process_label):
    log_level = set_log_level(log_file, level.upper())

    logging.basicConfig(
        filename=log_file,
        level=log_level,
        format=f'%(asctime)s [%(name)s] [{process_label}] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # notes: other options: [%(levelname)s]


def setup_logger(log_file, level="ERROR", process_label="MAIN"):
    """  set log level by handler for script or script area  """
    root = logging.getLogger()

    if not root.hasHandlers():
        set_format(log_file, level, process_label)
    else:
        set_logger(root, process_label, level.upper())

    return root


def change_logger(file_name, level, process_label):

    root = logging.getLogger()

    appdata_local = find_install()
    log_file = appdata_local / "logs" / file_name

    for h in root.handlers[:]:
        if isinstance(h, logging.FileHandler):
            root.removeHandler(h)

    set_format(log_file, level, process_label)

    return root, log_file


def logging_worker(queue, logger=None):
    log = logger if logger else logging
    while True:
        msg = queue.get()

        if msg is None:
            break
        try:
            level, message = msg
        except Exception:
            log.error(f"Invalid log format detected: {msg}")
            continue
        lvl = level.upper()
        log_levels = {
            'ERROR': log.error,
            'DEBUG': log.debug,
            'INFO': log.info,
            'WARNING': log.warning,
        }
        log_func = log_levels.get(lvl)
        if log_func:
            log_func(message)
        elif lvl == 'STOP':
            break
        else:
            log.error(f"Unknown log level: {message}")


def write_logs_to_logger(log_list, logger=None):
    log = logger if logger else logging

    for level, message in log_list:
        method = getattr(log, level.lower(), log.error)
        method(message)
    # for level, message in log_list:
    #     lvl = level.upper()
    #     if lvl == "DEBUG":
    #         log.debug(message)
    #     # elif lvl == "INFO":
    #     #     log.info(message)
    #     # elif lvl == "WARNING":
    #     #     log.warning(message)
    #     elif lvl == "ERROR":
    #         log.error(message)
    #     # elif lvl == "CRITICAL":
    #     #     log.critical(message)
    #     else:
    #         log.info(message)


def logs_to_queue(log_list, queue):
    for msg in log_list:
        queue.put(msg)


def check_log_perms(log_path):
    try:
        if log_path.exists():
            if log_path.stat().st_uid == 0:
                log_path.unlink()
        else:
            with open(log_path, 'a'):
                os.utime(log_path, None)
    except PermissionError:
        pass
