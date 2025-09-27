#                               09/26/2025
Currently working on a standalone python edition
This would use arrays as the main method see some speed improvements. mostly for if there are many new files
. the filesize would be smaller ect around 45kb

![Logo](https://i.imgur.com/sbZa1r3.png)

![Alt text](https://i.imgur.com/tKW7UEe.png)


## Porteus:
To save the backup in changes= type save-changesnew <br>
To save the backup in changes=EXIT:/   turn isolateBACK to true. then 'save-changesnew backup' and a backup will be made in /changes.bak beside /changes

With isolateBACK false changes are saved to /changes with rsync. You can also autosave to true which will add your $BASEDIR to changes commit and set it executable. this will save changes and
the backup on shutdown. backup to false and changes commit will call save-changesnew but wont do anything. autosave to false and changes commit is set to non-executable.

## Nemesis:
'save-changesnew y' or yes to auto sync backup on shutdown.
adds $BASEDIR to /ect/rc.d/rc.local_shutdown and the script sets itself to non-executable so it wont call again unless you recall y or yes
<p>&nbsp;</p>
<br><br><br>

Manual
https://docs.google.com/document/d/1EJAKd1v41LTLN74eXHf5N_BdvGYlfU5Ai8oWBDSGeho/edit?tab=t.0  
Porteus forums
https://forum.porteus.org/  <br><br>


Version: Standard     v1.0.9           save-changesnew        save-changesnewNMS <br><br>

Bash and python backends

Find new files, save changes in porteus/nemesis and RSync backup in changes=EXIT:/




Find files with new itime (change time) such as downloads from slackpkg and pacman. The modified time is preserved and only change time and accesss time are shown.
those are targeted and merged into the search.

Pull an .xzm with only the new files you want and also include all system new files in a .txt. 

This program has a filter that you can edit in /usr/local/save-changesnew/filter that can filter files from the search so only files you want to see are in the .xzm.

Uses two .gpgs for STATPST or persistent storage. logs.gpg and stats.gpg. stats.gpg contains actions Overwrite, Modified, Deleted, Replaced, Touched, Checksum, Metadata and Copy.

All searches are stored in logs.gpg and is the underlying principle of hybrid analysis. All searches with STATPST will include ha. So you can see what happened to them.

ANALYTICS is the same but its stored in /tmp/rc as a text file. Less secure but its owned by root and in TMPFS.

Rsync backup your changes folder in changes=EXIT:/ on porteus

Contantly up to date as I use this daily when developing.

2 modes. default  and mc.  Written strictly in bash and captures filenames with spaces commas quotes and new lines. <BR><BR><BR><BR>

<p> The script also updates the syslinux bootloader automatically to point to $BASEDIR/extramod. If you use a grub bootloader there  is a setting to point to the grub line number. Just make a new entry for graphics mode ie non changes. If your bootloader in on a different drive there is a setting to point to that.

for porteus a new entry called Graphics changes is made so one can be for loading extramod= ect.
</p>
<br><br><br><br>



  ## Recentchanges

   recentchanges. Developer buddy      make xzm     
   Provide ease of pattern finding ie what files to block we can do this a number of ways
   1) if a file was there (many as in more than a few) and another search lists them as deleted its either a sys file or not but unwanted nontheless
   2) Is a system file inherent to the specifc platform
   3) intangibles ie trashed items that may pop up infrequently and are not known about

  The purpose of this script is to save files ideally less than 5 minutes old. So when compiling or you dont know where some files are
or what changed on your system. So if you compiled something you call this script to build a module of it for distribution.
  If not using for developing call it a file change snapshot

We use the find command to list all files 5 minutes or newer. Filter it and then get to copying the files in a temporary staging directory in /tmp.
Then take those files and make an .xzm along with a transfer log to staging directory and file manifest of the xzm. A system search of all files for the specified time
is included less /tmp as that it confusing and too much info. <BR><BR><BR><BR>

<p> 'recentchanges' default search time of 5 minutes.</p>
<p> 'recentchanges n' where the time to search is specified in seconds.</p>
<p> There is also 'recentchanges -SRC'  which will look for a root folder from a compiled application and grab it and allow you to enter a custom name, preselected name or default name. So the application is packaged neatly. This can be used for other scripts ect. </p>
<BR><BR><BR><BR>





 ## Save Changes New        Nemesis

   this script works for two modes porteus nemesis graphics and changes.        

   graphics mode all changes are in memory so to implement changes saving this script will save changes to an .xzm. it will then modify the porteus.cfg
   and adds extramod=/mnt/sdx/extramod. so when the system boots it loads all your changes. if one already exists it will update it. So graphics changes mode wont
	load the graphics saves.

   Graphics changes mode all changes are saved to the hdd already. so this part will backup the changes to /changes.bak right beside it. including a logfile of the files 
   saved each time.

   Once the backup is made it only applies the deletions and additions so writes are minimal. Having a desktop icon makes it more likely you saved in the event 
   of a powerloss ect.

   Reasoning:
   1. if you boot with changes cheatcode it wont load the changes.xzm from graphics mode as its not in the module directory.
   2. if you use changes cheatcode nothing is changed its simply a backup of your changes. Thus if you like the system how it is run save-changesnew and create a backup of it.
   Then if something goes wrong you can simply delete your changes folder and rename changes.bak to changes

   If we can simplify the way of saving which is easy to use it will be more often done and can save you a lot of grief if you lose your data. As well as being minimally invasive it doesnt
   change anything on the system and is a worthwhile feature to add to developer buddy. I made developer buddy to also include saving changes on porteus 5.01 and porteus 5.1 so I decided
   developer buddy on nemesis should have a save feature as well and complete the module.

   Changes exit is not part of nemesis and rightfully so. It is a great variation of porteus that is minimal and fast. So we dont want to change anything to implement changes exit unless the author
   wants it. instead of doing any changes to nemesis which is beyond my capability I decided to use scripts I made with porteus and just provide a clean way of backing up your changes. So
   if youre in graphics mode your changes will persist if you run this script. It makes saving a one click step on the desktop. And if youre on any other mode it simply makes a backup of your changes very
   efficiently as it has minimals writes because you may already have a backup in place. <BR><BR><BR><BR>



   ## Save Changes New            Porteus

In addition to the RSync backup it saves your changes with rsync in porteus similar to changes commit.       /mnt/live/memory/changes ---->   /mnt/sdx/changes    -----> /mnt/sdx/changes.bak

 rsync backup to /changes.bak minimal writes as the backup would already be in place. Files are logged and its accurate
 
 to system specs with --delete. Added drive to drive while this is fast the preferable way is to not use drive to drive
 as it freezes the file system at that point in time. It does this by copying the files first to tmp. Its slower but good practice. However
on shutdown that wait would be too long. So drive to drive provides a way to save on that condition. It has so far worked without
any problems and is very fast. So both options are available depending on preference.


 Result saves your changes to your Changes=EXIT:  folder

 This is a proposed change to changes commit with directory method. All original lines are commented out to work with script

 working off of base save-changes scripts by
![Alt text](https://i.imgur.com/QVWc23x.jpeg)
 ![Alt text](https://i.imgur.com/4jOp3Ry.png) ![Alt text](https://i.imgur.com/3dXwKzW.png)
 ![Alt text](https://i.imgur.com/iZQ1s7t.png)
