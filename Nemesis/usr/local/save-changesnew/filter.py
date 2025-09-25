# Filter modified date: 07/24/2025       SN:049BN6KZ01
#
#	Notes: Nemesis 25.04
#

## Base var exclusions


def get_exclude_patterns(user):
    return [

        # Base var exclusions
        # combined more efficient*
         r'/var/(cache|run|tmp|lib/NetworkManager|lib/upower|log)',
        
        # r'/var/cache',
        # r'/var/run',
        # r'/var/tmp',
        # r'/var/lib/NetworkManager',
        # r'/var/lib/upower',
        # r'/var/log',
        
        # Additional exclusions
        r'/opt/porteus-scripts',
        r'/usr/share/mime',
        rf'/home/{user}/\.Xauthority',
        rf'/home/{user}/\.local/state/wireplumber',
        
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
        rf'/home/{user}/\.config',
        r'/usr/local/save-changesnew/logs\.gpg',
        r'/usr/local/save-changesnew/recent\.gpg',
        r'/usr/local/save-changesnew/stats\.gpg',
        r'/usr/local/save-changesnew/flth\.csv',
        
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
        
        #Chromium exclusions (uncomment if needed)
        r'ungoogled',
       
    #    Now we get into the important directories. Do we exclude at the risk of deleting our program? Tread carefully

    #    Very carefully select only starting /etc/    <------  We can remove this filter if needed


    #    we dont want  /etc/
       #r'^/etc'  # Uncomment to exclude /etc
    ]

# Filter modified date: 07/25/2025       SN:049BN6KZ01
#
#	Notes: has porteus 5.01 and 5.1 built in
#
#  Full modularity only one filter needed for version 3       used to be a copy in compilesearch.sh you used to have to update as well
# $1 first file $2 user $3 second file

#def get_exclude_patterns(user):
#    return [
#        r'/var/cache',
#        r'/var/run',
#        r'/var/tmp',
#        r'/var/lib/NetworkManager',
#        r'/var/lib/upower',
#        r'/var/log',
#        r'/opt/porteus-scripts',
#        r'/usr/share/mime',
#        r'/usr/share/glib-2\.0/schemas',
#
#        # Porteus 5.01
#        r'/usr/lib64/libXc',
#        r'/usr/lib64/libudev',
#        r'/var/db/sudo/lectured/1000',
#        rf'/home/{user}/\.config/dolphinrc',
#        rf'/home/{user}/\.config/konsolerc',
#        rf'/home/{user}/\.config/featherpad/fp\.conf',
#        r'\.config/glib-2\.0/settings/keyfile',
#
#        r'\.bash_history',
#        r'\.cache',
#        r'\.dbus',
#        r'\.gvfs',
#        r'\.gconf',
#        r'\.gnupg',
#        r'\.local/share',
#        r'\.xsession',
#        rf'/home/{user}/\.config',
#        r'/usr/local/save-changesnew/logs\.gpg',
#        r'/usr/local/save-changesnew/recent\.gpg',
#        r'/usr/local/save-changesnew/stats\.gpg',
#        r'/usr/local/save-changesnew/flth\.csv',
#        r'/root/\.auth',
#        r'/root/\.config',
#        r'/root/\.lesshst',
#        r'/root/\.xauth',
#
#      Now we get into the important directories. Do we exclude at the risk of deleting our program? Tread carefully
#
#      Very carefully select only starting /etc/    <------  We can remove this filter if needed
#
#
#      we dont want  /etc/
#      r'^/etc'  # Uncomment to exclude /etc
#    ]

# Windows
#
# 
# local_cache = os.getenv('LOCALAPPDATA')    # Program directories
#


#
#def get_exclude_patterns(user):
#    
#    temp_dir = re.escape(tempfile.gettempdir())
#
#    return [
#        temp_dir,
#        rf'C:\\Users\\{escaped_user}\\AppData\\Local\\Temp',
#
#        # Custom dirs
#
#        # Inclusion from script
#        rf'C:\\Users\\{user}\\AppData\\Programs\\Recentchgs\\recent\.gpg',
#        rf'C:\\Users\\{user}\\AppData\\Programs\\Recentchgs\\flth\.csv',
#        rf'C:\\Users\\{user}\\AppData\\Local\\Packages\\[^\\]+\\LocalCache'
#     ]
#

#
#      Now we get into the important directories. Do we exclude at the risk of deleting our program? Tread carefully
#
#      Very carefully select only starting ''  <------  We can remove this filter if needed
#
#
#      we dont want
#        # Uncomment to exclude
#    ]
