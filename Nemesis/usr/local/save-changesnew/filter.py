# Filter modified date: 09/27/2025       SN:049BN6KZ01
#
#	Notes: Nemesis 25.04
#

## Base var exclusions


def get_exclude_patterns():
    return  [

        # Base var exclusions
        r'/var/cache',
        r'/var/run',
        r'/var/tmp',
        r'/var/lib/NetworkManager',
        r'/var/lib/upower',
        r'/var/log',
        
        # Additional exclusions
        r'/opt/porteus-scripts',
        r'/usr/share/mime',
        rf'/home/{{user}}/\.Xauthority',
        rf'/home/{{user}}/\.local/state/wireplumber',
        
        r'.bash_history',
        r'.cache',
        r'.dbus',
        r'.gvfs',
        r'.gconf',
        r'.gnupg',
        r'.local/share',
        r'.local/state',
        r'.xsession',
        
        # Inclusions from script
        rf'/home/{{user}}/\.config',
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
        r'ungoogled'
       
    #    Now we get into the important directories. Do we exclude at the risk of deleting our program? Tread carefully

    #    Very carefully select only starting /etc/    <------  We can remove this filter if needed


    #    we dont want  /etc/
       #r'^/etc'  # Uncomment to exclude /etc
    ]