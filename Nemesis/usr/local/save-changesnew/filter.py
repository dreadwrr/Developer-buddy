# Filter modified date: 07/25/2025       SN:049BN6KZ01
#
#	Notes: has porteus 5.01 and 5.1 built in
#
#  Full modularity only one filter needed for version 3       used to be a copy in compilesearch.sh you used to have to update as well
# $1 first file $2 user $3 second file
import re

def get_exclude_patterns(user):
    return [
        r'/var/cache',
        r'/var/run',
        r'/var/tmp',
        r'/var/lib/NetworkManager',
        r'/var/lib/upower',
        r'/var/log',
        r'/opt/porteus-scripts',
        r'/usr/share/mime',
        r'/usr/share/glib-2\.0/schemas',
        r'/usr/lib64/libXc',
        r'/usr/lib64/libudev',
        r'/var/db/sudo/lectured/1000',
        # user-specific exclusions:
        rf'/home/{re.escape(user)}/\.config/dolphinrc',
        rf'/home/{re.escape(user)}/\.config/konsolerc',
        rf'/home/{re.escape(user)}/\.config/featherpad/fp\.conf',
        r'\.config/glib-2\.0/settings/keyfile',
        r'\.bash_history',
        r'\.cache',
        r'\.dbus',
        r'\.gvfs',
        r'\.gconf',
        r'\.gnupg',
        r'\.local/share',
        r'\.xsession',
        rf'/home/{re.escape(user)}/\.config',
        r'/usr/local/save-changesnew/logs\.gpg',
        r'/usr/local/save-changesnew/recent\.gpg',
        r'/usr/local/save-changesnew/stats\.gpg',
        r'/usr/local/save-changesnew/flth\.csv',
        r'/root/\.auth',
        r'/root/\.config',
        r'/root/\.lesshst',
        r'/root/\.xauth',
    ]