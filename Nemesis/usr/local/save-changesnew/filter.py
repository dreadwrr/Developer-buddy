# Filter modified date: 01/08/2025       SN:049BN6KZ01
#
#   Notes: Nemesis 25.04
#
#  [^/]+ match up to only one directory level example somepath/[^/]+/thisdir
# /.*?/ non greedily match up to and including first directory found. ie somepath/.*?/thisdir
# /home/{{user}} is replaced with /root if user is root
# Example from below to combine but not done here for readability
# r'/var/cache',
# r'/var/run',
# can be combined as
# r'^/var/(cache|run)'

_filter = [

        # Base var exclusions
        r'/var/cache',
        r'/var/run',
        r'/var/tmp',
        r'/var/lib/NetworkManager',
        r'/var/lib/upower',
        r'/var/log',

        # Additional exclusions
        r'/usr/share/mime',
        r'/home/{{user}}/\.config',
        r'/home/{{user}}/\.Xauthority',
        r'/home/{{user}}/\.local/state/wireplumber',

        r'\.bash_history',
        r'\.cache',
        r'\.dbus',
        r'\.gvfs',
        r'\.gconf',
        r'\.gnupg',
        r'\.local/share',
        r'\.local/state',
        r'\.xsession',

        # r'/root/\.Xauthority',
        # r'/root/\.local/state/wireplumber',
        # r'/root/\.auth',
        # r'/root/\.config',
        # r'/root/\.lesshst',
        # r'/root/\.xauth',

        # Firefox-specific exclusions
        r'release/cookies\.sqlite-wal',
        r'release/sessionstore-backups',
        r'release/aborted-session-ping',
        r'release/cache',
        r'release/datareporting',
        r'release/AlternateServices\.bin',

        # Chromium exclusions (uncomment if needed)
        # r'ungoogled'

    ]


# filter hits to reset on Cache clear. copy literal items from /usr/local/save-changesnew/filter.py to. resets to 0
_filterhitRESET = [
    r'/home/{{user}}/\.config',
    r'/home/{{user}}/\.Xauthority',
    r'/home/{{user}}/\.local/state/wireplumber',
    r'/root/\.Xauthority',
    r'/root/\.local/state/wireplumber',
    r'\.cache',
    r'\.gnupg',
    r'\.local/share'

]
