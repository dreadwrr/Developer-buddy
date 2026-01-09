#                               01/08/2025
Python edition <br>
Update soon to be released with finalized ha and improvements <br><br>
Differences from bash and bash\python backends is the find command is streamed with the main search written in python.


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

