import sqlite3
import traceback


def create_table(c, table, unique_columns, e_cols=None):
    columns = [
        'id INTEGER PRIMARY KEY AUTOINCREMENT',
        'timestamp TEXT',
        'filename TEXT',
        'changetime TEXT',
        'inode INTEGER',
        'accesstime TEXT',
        'checksum TEXT',
        'filesize INTEGER',
        'symlink TEXT',
        'owner TEXT',
        '`group` TEXT',
        'permissions TEXT',
        'casmod TEXT',
        'target TEXT',
        'lastmodified TEXT'
    ]
    if e_cols:
        if isinstance(e_cols, str):
            e_cols = [col.strip() for col in e_cols.split(',') if col.strip()]
        columns += e_cols

    col_str = ',\n      '.join(columns)
    unique_str = ', '.join(unique_columns)
    sql = f'''
    CREATE TABLE IF NOT EXISTS {table} (
    {col_str},
    UNIQUE({unique_str})
    )
    '''
    c.execute(sql)

    sql = 'CREATE INDEX IF NOT EXISTS'

    if table == 'logs':
        c.execute(f'{sql} idx_logs_checksum ON logs (checksum)')
        c.execute(f'{sql} idx_logs_filename ON logs (filename)')
        c.execute(f'{sql} idx_logs_checksum_filename ON logs (checksum, filename)')  # Composite
    else:
        c.execute(f'{sql} idx_sys_checksum ON sys (checksum)')
        c.execute(f'{sql} idx_sys_filename ON sys (filename)')
        c.execute(f'{sql} idx_sys_checksum_filename ON sys (checksum, filename)')


def create_db(database, action=None):
    print('Initializing database...')

    conn = sqlite3.connect(database)
    c = conn.cursor()

    create_table(c, 'logs', ('timestamp', 'filename', 'changetime', 'checksum'), ['hardlinks INTEGER', 'mtime_us INTEGER'])

    create_table(c, 'sys', ('timestamp', 'filename', 'changetime', 'checksum'), ['count INTEGER', 'mtime_us INTEGER'])

    c.execute('''
    CREATE TABLE IF NOT EXISTS stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        timestamp TEXT,
        filename TEXT,
        changetime TEXT,
        UNIQUE(timestamp, filename, changetime)
        )
    ''')
    conn.commit()
    if action:
        return conn
    else:
        conn.close()


def insert(log, conn, c, table, add_column=None):  # Log, sys

    columns = [
        'timestamp', 'filename', 'changetime', 'inode', 'accesstime',
        'checksum', 'filesize', 'symlink', 'owner', '`group`',
        'permissions', 'casmod', 'target', 'lastmodified'
    ]
    if add_column:
        if isinstance(add_column, (tuple, list)):
            columns.extend(add_column)
        else:
            raise TypeError("add_column must be str, tuple, or list")
    placeholders = ', '.join(['?'] * len(columns))
    col_str = ', '.join(columns)
    c.executemany(
        f'INSERT OR IGNORE INTO {table} ({col_str}) VALUES ({placeholders})',
        log
    )

    if table == 'logs':
        blank_row = tuple([None] * len(columns))
        c.execute(
                f'INSERT INTO {table} ({col_str}) VALUES ({", ".join(["?"]*len(columns))})',
                blank_row
        )

    conn.commit()


def insert_if_not_exists(action, timestamp, filename, changetime, conn, c):  # Stats
    timestamp = timestamp or None
    c.execute('''
    INSERT OR IGNORE INTO stats (action, timestamp, filename, changetime)
    VALUES (?, ?, ?, ?)
    ''', (action, timestamp, filename, changetime))
    conn.commit()


def get_recent_changes(filename, cursor, table, e_cols=None):
    columns = [
        "timestamp", "filename", "changetime", "inode",
        "accesstime", "checksum", "filesize", "symlink",
        "owner", "`group`", "permissions", "casmod",
        "target"
    ]
    if e_cols:
        if isinstance(e_cols, str):
            e_cols = [col.strip() for col in e_cols.split(',') if col.strip()]
        columns += e_cols

    col_str = ", ".join(columns)

    query = f'''
        SELECT {col_str}
        FROM {table}
        WHERE filename = ?
        ORDER BY timestamp DESC
        LIMIT 1
    '''
    cursor.execute(query, (filename,))
    return cursor.fetchone()


def table_has_data(conn, table_name):
    c = conn.cursor()
    c.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table_name,))
    if not c.fetchone():
        c.close()
        return False
    c.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
    res = c.fetchone() is not None
    c.close()
    return res


def collision(cursor, is_sys):
    try:
        if is_sys:
            tables = ['logs', 'sys']
            union_sql = " UNION ALL ".join([
                f"SELECT filename, checksum, filesize FROM {t} WHERE checksum IS NOT NULL" for t in tables
            ])
            query = f"""
                WITH combined AS (
                    {union_sql}
                )
                SELECT a.filename, b.filename, a.checksum, a.filesize, b.filesize
                FROM combined a
                JOIN combined b
                ON a.checksum = b.checksum
                AND a.filename < b.filename
                AND a.filesize != b.filesize
                ORDER BY a.checksum, a.filename
            """
        else:
            query = """
                SELECT a.filename, b.filename, a.checksum, a.filesize, b.filesize
                FROM logs a
                JOIN logs b
                ON a.checksum = b.checksum
                AND a.filename < b.filename
                AND a.filesize != b.filesize
                WHERE a.checksum IS NOT NULL
                ORDER BY a.checksum, a.filename
            """

        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Database error in collision detection: {type(e).__name__} : {e}")
        return []


# 12/15/2025
def detect_copy(filename, inode, checksum, cursor, ps):
    if ps:
        query = '''
            SELECT filename, inode
            FROM logs
            WHERE checksum = ?
            UNION ALL
            SELECT filename, inode
            FROM sys
            WHERE checksum = ?
        '''
        cursor.execute(query, (checksum, checksum))
    else:
        query = '''
            SELECT filename, inode
            FROM logs
            WHERE checksum = ?
        '''
        cursor.execute(query, (checksum,))

    candidates = cursor.fetchall()
    # for o_filename, o_inode in candidates:
    #     if o_filename != filename or o_inode != inode:
    #         return True
    for _, o_inode in candidates:
        if o_inode != inode:
            return True

    return None


def increment_f(conn, c, records, logger=None):

    if not records:
        return False

    inserted_entry = []

    try:
        for record in records:

            c.execute("""
                INSERT OR IGNORE INTO sys (
                    timestamp, filename, changetime, inode, accesstime, checksum,
                    filesize, symlink, owner, `group`, permissions, casmod, target,
                    lastmodified, count, mtime_us
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, record)

            if c.rowcount > 0:
                inserted_entry.append(record[1])

        for filename in inserted_entry:
            c.execute("UPDATE sys SET count = count + 1 WHERE filename = ?", (filename,))
        conn.commit()
        return True

    except sqlite3.OperationalError as e:
        conn.rollback()
        print(f"Error while insert sys records skipping was unable to complete and then update count. increment_f {type(e).__name__} : {e}  \n{traceback.format_exc()}")
    except Exception as e:
        err = f"Error increment_f table sys {type(e).__name__} {e}"  # \n{traceback.format_exc()}
        print(err)
        if logger:
            logger.error(err, exc_info=True)
    return False
