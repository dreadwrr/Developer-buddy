# Filter modified date: 02/26/2025       SN:049BN6KZ01
#
#   Notes: has porteus 5.01 and 5.1 built in
#
#  [^/]+ match up to only one directory level example somepath/[^/]+/thisdir
# /.*?/ non greedily match up to and including first directory found. ie somepath/.*?/thisdir
#
# Example from below to combine but not done here for readability
# r'/var/cache',
# r'/var/run',
# can be combined as
# r'^/var/(cache|run)'
def get_exclude_patterns():

    return [

        # Base var exclusions
        r'/var/cache',
        r'/var/run',
        r'/var/tmp',
        r'/var/lib/NetworkManager',
        r'/var/lib/upower',
        r'/var/log',

        # Additional exclusions
        r'/usr/share/mime',
        r'/home/{{user}}/\.Xauthority',
        r'/usr/share/glib-2\.0/schemas',

        r'/usr/lib64/libXc',
        r'/usr/lib64/libudev',
        r'/var/db/sudo/lectured/1000',
        r'/home/{{user}}/\.config',
        r'/home/{{user}}/\.config/dolphinrc',
        r'/home/{{user}}/\.config/konsolerc',
        r'/home/{{user}}/\.config/featherpad/fp\.conf',
        r'/\.config/glib-2\.0/settings/keyfile',

        r'\.bash_history',
        r'\.cache',
        r'\.dbus',
        r'\.gvfs',
        r'\.gconf',
        r'\.gnupg',
        r'\.local/share',
        r'\.local/state',
        r'\.xsession',

        # Inclusions from script
        # r'/usr/local/save-changesnew/ctimecache\.gpg',
        # r'/usr/local/save-changesnew/recent\.gpg',
        # r'/usr/local/save-changesnew/flth\.csv',

        r'/root/\.auth',
        r'/root/\.config',
        r'/root/\.lesshst',
        r'/root/\.xauth',

        # Firefox-specific exclusions

        r'release/cookies\.sqlite-wal',
        r'release/sessionstore-backups',
        r'release/aborted-session-ping',
        r'release/cache',
        r'release/datareporting',
        r'release/AlternateServices\.bin',

        # Chromium exclusions (uncomment if needed)
        # r'ungoogled'

        #    Now we get into the important directories. Do we exclude at the risk of deleting our program? Tread carefully

        #    Very carefully select only starting /etc/    <------  We can remove this filter if needed


        #    we dont want  /etc/
        # r'^/etc'  # Uncomment to exclude /etc
    ]
