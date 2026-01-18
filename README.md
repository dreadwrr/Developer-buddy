#                               01/17/2026
Python edition <br>
Released v1.2.6-py1 with finalized, inotify wait and other features!<br><br>
Updated launch script with switching done in python. To allow for compatibility with wayland and other distros<br><br> 
Differences from bash and bash\python backends is the find command is streamed with the main search written in python. <br><br>
Full logging system, xRC inotify, isdiff, logic, display, filterhits, process hybrid analysis, filter output pretty much all the logic rewritten in python
slight change in data handling with use of arrays vs files in bash ( rout the file that handles ha output and file actions)
the filter is filter.py and there is a config.toml <br><br>


![Logo](https://i.imgur.com/sbZa1r3.png)

![Alt text](https://i.imgur.com/tKW7UEe.png)


## Porteus:
To save the backup in changes= type save-changesnew <br>
To save the backup in changes=EXIT:/   turn isolateBACK to true. then 'save-changesnew backup' and a backup will be made in /changes.bak beside /changes

With isolateBACK false changes are saved to /changes with rsync. You can also autosave to true which will add your $BASEDIR to changes commit and set it executable. this will save changes and
the backup on shutdown. backup to false and changes will be saved by changes commit but wont do anything to the backup. autosave to false and changes commit is set to non-executable.

## Nemesis:
'save-changesnew y' or yes to auto sync backup on shutdown.
adds $BASEDIR to /ect/rc.d/rc.local_shutdown and the script sets itself to non-executable so it wont call again unless you recall y or yes
<p>&nbsp;</p>
<br><br><br>

Manual
https://docs.google.com/document/d/1EJAKd1v41LTLN74eXHf5N_BdvGYlfU5Ai8oWBDSGeho/edit?tab=t.0  
Porteus forums
https://forum.porteus.org/  <br><br>

