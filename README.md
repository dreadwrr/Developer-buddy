#                               09/11/2025


![Logo](https://i.imgur.com/sbZa1r3.png)

![Alt text](https://i.imgur.com/tKW7UEe.png)
Manual
https://docs.google.com/document/d/1EJAKd1v41LTLN74eXHf5N_BdvGYlfU5Ai8oWBDSGeho/edit?tab=t.0  
Porteus forums
https://forum.porteus.org/  <BR><BR>

Porteus changes=    backup will be made with save-changesnew
changes=EXIT:/     save-changesnew backup. that will make the backup with appropriate isolateBACK interlock


Brought _uid_L for porteus graphics mode! for non changes=EXIT:/ users.

## Porteus:
To save the backup in changes= type save-changesnew
To save the backup in changes=EXIT:/   turn isolateBACK to true. then 'save-changesnew backup' and a backup will be made in /changes.bak beside /changes

With isolateBACK false changes are saved to /changes. You can also autosave to true which will add your $BASEDIR to changes commit and save changes on shutdown.
backup to false and changes commit wont do anything on backup
autosave to false and changes commit is set to non-executable

## Nemesis:
save-changesnew y or yes to auto sync backup on shutdown.
adds $BASEDIR to /ect/rc.d/rc.local_shutdown and the script sets itself to non-executable so it wont call again unless you recall y or yes


Version: Standard                save-changesnew        save-changesnewNMS <br><br>

Bash and python backends

Find new files, save changes in porteus/nemesis and RSync backup in changes=EXIT:/




Find files withnew atime such as slackpkg to appear in searches. The modified time is preserved metadata and wont showup in regular searches.

Pull an .xzm with only the new files you want and also include all system new files

This program has a filter that you can edit in /usr/local/save-changesnew/filter that can filter files from the search so only files you want to see are in the .xzm.

Uses two .gpgs for STATPST or persistent storage. logs.gpg and stats.gpg. stats.gpg contains actions Overwrt, Modified, Deleted, Replaced, Touched, Csumc ect.

All searches are stored in logs.gpg and is the underlying principle of hybrid analysis. All searches with STATPST will include ha. Not only can you see new files but 
exactly what happened to them.

Rsync backup your changes folder in changes=EXIT:/ on porteus

Contantly up to date as I use this daily when developing.

2 modes. normal  and mc.  Written strictly in bash. <BR><BR><BR><BR>





  Recentchanges

   recentchanges. Developer buddy      make xzm     
   Provide ease of pattern finding ie what files to block we can do this a number of ways
   1) if a file was there (many as in more than a few) and another search lists them as deleted its either a sys file or not but unwanted nontheless
   2) Is a system file inherent to the specifc platform
   3) intangibles ie trashed items that may pop up infrequently and are not known about

  The purpose of this script is to save files ideally less than 5 minutes old. So when compiling or you dont know where some files are
or what changed on your system. So if you compiled something you call this script to build a module of it for distribution.
  If not using for developing call it a file change snapshot

We use the find command to list all files 5 minutes or newer. Filter it and then get to copying the files in a temporary staging directory in /tmp.
Then take those files and make an .xzm along with a transfer log to staging directory and file manifest of the xzm  <BR><BR><BR><BR>







  Save Changes New        Nemesis

   this script works for two modes porteus nemesis graphics and changes.        

   graphics mode all changes are in memory so to implement changes saving this script will save changes to an .xzm. it will then modify the porteus.cfg
   and adds extramod=/mnt/sdx/extramod. so when the system boots it loads all your changes. if one already exists it will update it. So graphics changes mode wont
	load the graphics saves.

   Graphics changes mode all changes are saved to the hdd already. so this part will backup the changes to /changes.bak right beside it.

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



   Save Changes New            Porteus

In addition to the RSync backup it saves your changes with rsync in porteus.       /mnt/live/memory/changes ---->   /mnt/sdx/changes    -----> /mnt/sdx/changes.bak

 rsync backup to /changes.bak minimal writes as the backup would already be in place. Files are logged and its accurate
 
 to system specs with --delete. Added drive to drive while this is fast the preferable way is to not use drive to drive
 as it freezes the file system at that point in time. But on shutdown that wait would be too long. So drive to drive provides
 a way to save on that condition. So both options are available depending on preference.


 Result saves your changes to your Changes=EXIT:  folder

 This is a proposed change to changes commit with directory method. All original lines are commented out to work with script

 working off of base save-changes scripts by
![Alt text](https://i.imgur.com/QVWc23x.jpeg)
 ![Alt text](https://i.imgur.com/4jOp3Ry.png) ![Alt text](https://i.imgur.com/3dXwKzW.png)
 ![Alt text](https://i.imgur.com/iZQ1s7t.png)
