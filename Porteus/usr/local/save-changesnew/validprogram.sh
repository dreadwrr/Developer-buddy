#!/bin/bash
#     recentchanges general functions    validprogram       gettime                                                                07/4/2025
#
#   The purpose of this function is to find out if there is a valid program in the logfile. There are number of ways we can determine if it is an application. You could go 
#into great depth determining if it is as such. It however is not necessary. We likely already have a valid application within the contents of the log. The problem is there 
#could be bogus files within it. If we can get the root of the application we can cat the logfile and grep only the base directory thus cutting out bogus files.
#
#
# 
#This function returns the root directory or null if it is in  /  of system
validprogram() {
local LOGFILE=$1
#local MAXCOUNT=0
local FCOUNT=0
local BASEDIR=""
local DEPTH=0
#local ROOTDIR=""
local y=0
local p=0
local z=""
local strt=0
local ABSTRING=""
local BCSTRING=""
local CDSTRING=""
#Array notes
#
#myarr[$index]=$BASEDIR
#index=$(($index+1))        
#a=( ${myarr[2]} ); echo ${a[3]} 

#Preliminary design
#
#Single out the program in a logfile
# Find the highest count of files
#
# There very well could be several sub directories thus outnumbering the application root directories.
#we will have to take care of that after this section. For now lets get the highest file count.
#

# Preliminary algorithm draft
#
#
# sed -E 's/^([^/]*[/]){2}//'      print everything after nth delimiter  /  ie  /thisdir/thatvar/thisdir/      thatvar/thisdir/
#
#
# sed -E 's/(^([^/]*[/]){1}).*/\1/'  print everything up to nth delimiter /  ie   /thisvar/thatvar/thisdir/     /thisvar/thatvar/
# sed -E 's/(^([^/]*[/]){3}[^/]*).*/\1/'  print everything up to ^            ie  /this/var/thatvar/thisdir/     /thisvar/thatvar/thisdir

# echo $string | awk NF=3 FS='/' OFS='/'    print everything up to nth delimiter ie    /thisvar/thatvar/thisdir/    /thisvar/thatvar
#
#
#while IFS= read x
#do
   
#    MAXCOUNT=$( grep -c "${x}"$ $LOGFILE)
#	d=$( echo "${x}" | awk -F '/' '{print NF-1}')   #Depth  ie /home/guest/myapp/ has a depth of 4
	
#    if [ $MAXCOUNT -gt $FCOUNT ] && [ $d -ge 4 ]; then
#        FCOUNT=$MAXCOUNT
#        BASEDIR="${x}"
#        DEPTH=$d  
#    fi
#done < $LOGFILE
#unset IFS

#End preliminary design


# There are certain things that would constitute a root directory. Is there a /bin /lib64 /lib /man    /usr ?
#
#	The following is an example with files in each directory per occurence 1 file
#
#	The recursion would stop at /Downloads 
#
#	/home/guest/Downloads/myapp/bin/
#	/home/guest/Downloads/myapp/bin/
#	/home/guest/Downloads/myapp/lib64/
#	/home/guest/Downloads/myapp/man/
#	/home/guest/Downloads/myapp/man/
#	/home/guest/Downloads/myapp/man5/docs/
#	/home/guest/Downloads/myapp/man5/docs/
#	/home/guest/Downloads/myapp/man5/docs/
#	/home/guest/Downloads/myapp/man5/docs/
#	/home/guest/Downloads/myapp/man5/docs/
#	/home/guest/Downloads/myapp/man5/docs/ 
#	/home/guest/Downloads/Schedules/
#   /home/guest/Downloads/myfile.mp3              <-------------- Doesnt belong

#	You can see that unless specific conditions are known this is as close as we can get  /home/guest/Downloads/      1 file would be included with the .xzm of the application
#
#
#	We can pull the times from         /home/guest/Downloads/myapp/man5/docs/                 add a hysterisis of 2 minutes. so exclude any files before and after that time frame
#																						and maybe  /home/guest/Downloads/myfile.mp3      would disapear from the list

#	Another consideration that I will implement is we are at /Downloads/ look ahead next Downloads/Apps are there files? No then that is the root.   /home/guest/Downloads/myapp/


#	We can also use a system template as   /home/guest/Downloads/     is a set system directory therefor the root is   /myapp/
#   see function   insetdirectory()
#
#   So a configuration section in the variables could be made for     hystersis    
#	As well as more condition could be added to the check. If we arrive at Downloads/ and no /bin or /lib64 go to the next one. Thus we arrive at   /myapp/
#
# 	Last point of note
#
# 	But the problem with thinking something is a certain way often breaks. thus its better to encompass all conditions. and include   /home/guest/Downloads/myfile.mp3
#


# Begin finding root dir
#
# We could be in a subdirectory that has more files than the root. If we traverse down from the start and the directory count from the list
# increases we have found the root dir.


#	If we have a list of directories grepped from the unique directory   /var/anydir/           as an example   what if our app is        /var/thisdir/randomdir/myapp/      and       /var/thisdir/randomdir/otherapp/
#
# you can see the algorithm will stop at         /var/thisdir/randomdir/    as that is the common path from the list.        But what if we excluded any file from the list that doesnt belong?
#
# You can do this two ways. From the time any files within the search time. Or add a hystersis within the search time.    If we iterate over the list and check  does this path have more files than whats in the list?
# If it does then we can delete it from the list. It maybe is a cachedir? or  a file was added 30 seconds after compiling or during compiling?


# Clean up list plan to add
#

# Final algorithm
BASEDIR=$( cat $LOGFILE | uniq -c | sort -sr | head -n 1 | awk '{print $2}')        # The target files - The largest number of file count above example is  /docs/
DEPTH=$( echo "${BASEDIR}" | awk -F '/' '{print NF-1}')                                 # The number of fields - The depth of  /home/guest/Downloads/myapp/man5/docs/
FCOUNT=$( grep -c "${BASEDIR}" $LOGFILE)                                                # Occurences in logfile


#
#  Plan to add from starting point. Check log if we arrive at a possible root dir. Do a system check compared to log count. If there are more system files than whats in the log
# Then we havent found the root. Try the next one  (bisecting common path still) and if it becomes the same then thats the root dir. Otherwise Exit 1.
#
#
#

# If it has a depth of 3       /thisdir/thatdir/    return    /thisdir/thatdir/


#if (( DEPTH == 3 )); then
#	BASEDIR=$( echo "${BASEDIR}" | sed -E 's/(^([^/]*[/]){3}).*/\1/')      #First two fields for unique identification   /mydir/thisdir/     # | sed -E 's/\/$//'
#	echo "${BASEDIR}"
	
# Find the longest common path      traditional recurse until the count goes down. then stop and you have your root.
#elif (( DEPTH < 3 )); then

#else
p=0

#Check if it in a set system directory and adjust where we start in loop
z=$( insetdirectory)   

if [ "$z" != "" ]; then
	#If there are few files then they are in the system directory
	if (( z = DEPTH)); then
    	strt=$z
    #Proceed regularly and it is the root file in the system directory
    else
    	strt=$(( z + 1))
    fi
else
	#Start from /Dir1/ or start from the beginning because its not in a system directory
    strt=2
fi

for ((i=strt; i<=DEPTH; i++))
do

	IDIR=$( echo "${BASEDIR}" | cut -d '/' -f 1-$i)

	y=$( grep -c "^${IDIR}" $LOGFILE)
    #echo $CDSTRING >> /home/guest/test.txt
	if (( y >= p )); then
		p=$y
        
		CDSTRING=$IDIR
	else
		break
	fi

    # Notes
	#Get the highest column count
	#BCSTRING=$( awk -F '/' -v ccnt="$i" '{ print $ccnt }' $LOGFILE | uniq -c | sort -sr | head -n 1 | awk '{ print $2}')           #/thisdir/thatdir/overdir/  returns path               <---- Alternative turn the highest column print up to that column
	#BCSTRING=$( echo "${BASEDIR}" | cut -d '/' -f $i)          i start at 2		
	#BCSTRING="${BCSTRING#?}" 						<---- Alternative  strip the first  '/'
	#ABSTRING="${ABSTRING}/${BCSTRING}"
    #CDSTRING=$ABSTRING
	#y=$( grep -c "^${ABSTRING}" $LOGFILE)
	#if  echo "${BASEDIR}" | grep -q "${ABSTRING}"; then                            <----   Alternative         does it match part of the line from out   BASEDIR    (highest file count)
	#	if (( y > FCOUNT )); then
	#		CDSTRING=$ABSTRING
	#	fi
	#else
	#	break			
	#fi
done

BASEDIR=$CDSTRING
echo "${BASEDIR}"

#fi

#   Other logic
#
#
#
#Is the particular application in a set directory or system directory?
#locationchk=$( insetdirectory "${BASEDIR}")

#if [ "$locationchk" != "" ]; then
#	BASEDIR="${locationchk}"
#else


#Previous draft recurvisely backwards
#else		#Depends where we are ? We alredy know its not a sytem directory.       The typical directory structure is more files are in subfolders ie   /bin  /man  /lib64  so we are probably in a subdirectory
		#																																								therefor we drop a directory
		#if (( d > 2 )); then                 #It has a range of 4 or 3  :   that means     /mydir/thisdir/thatdir/   or    /mydir/thisdir/    so  either 3 or 2 directory depth
										
		#	BASEDIR=$( echo "${BASEDIR}" | sed -E 's/(^([^/]*[/]){3}).*/\1/' | sed -E 's/\/$//')      #First two fields for unique identification   /mydir/thisdir/
																							  	# remove trailing /
		#else
		#It has a range of 2 : that means             /mydir/         root directory
		#	BASEDIR=$( echo "${BASEDIR}" | sed -E 's/(^([^/]*[/]){2}).*/\1/' | sed -E 's/\/$//')      #First field is unique    app was created in /   or root of system
		#fi

	#if (( d > 4 )); then
	
    	#We recurse to see if we are in a subdirectory with more files than root
    	#ROOTDIR="${BASEDIR%/*}"
    	#ROOTDIR="${ROOTDIR%/*}"
    	#while [ "$ROOTDIR" != "" ] && [ $d -gt 4 ]
    	#do
	
			#y=$( grep -c "${ROOTDIR}" $LOGFILE)
				
			#if (( y > FCOUNT )); then
			
    		#	FCOUNT=$y
    		#	BASEDIR="${ROOTDIR}"
			#fi
        	
        	#(( d-- ))
			#ROOTDIR="${ROOTDIR%/*}"
    	#done
	#else
	
		#Depends where we are ? We alredy know its not a sytem directory.       The typical directory structure is more files are in subfolders ie   /bin  /man  /lib64  so we are probably in a subdirectory
		#																																								therefor we drop a directory
		#if (( d > 2 )); then                 #It has a range of 4 or 3  :   that means     /mydir/thisdir/thatdir/   or    /mydir/thisdir/    so  either 3 or 2 directory depth
										
		#	BASEDIR=$( echo "${BASEDIR}" | sed -E 's/(^([^/]*[/]){3}).*/\1/' | sed -E 's/\/$//')      #First two fields for unique identification   /mydir/thisdir/
																							  	# remove trailing /
		#else
				##It has a range of 2 : that means             /mydir/         root directory
		#	BASEDIR=$( echo "${BASEDIR}" | sed -E 's/(^([^/]*[/]){2}).*/\1/' | sed -E 's/\/$//')      #First field is unique    app was created in /   or root of system
		#fi
			
		#BASEDIR="${BASEDIR%/*}"     <----- also removes trailing slash
	#fi
   	
#fi

#We can now return the rootdir
#echo "${BASEDIR}"
}

# Test if directory is in a system directory and return the root directory
insetdirectory() {

local result
local newdir
local d
local template=()
	
template+=("/home/$USR/Downloads/")
template+=("/home/$USR/Pictures/")
template+=("/home/$USR/Desktop/")
template+=("/home/$USR/Documents/")
template+=("/home/$USR/Music/")
template+=("/home/$USR/Pictures/")
template+=("/home/$USR/Public/")
template+=("/home/$USR/Videos/")
template+=("/home/$USR/")
template+=("/bin/")
template+=("/etc/")
template+=("/lib/")
template+=("/lib64/")
template+=("/opt/")
template+=("/root/")  #more than one dir
template+=("/sbin/")
template+=("/usr/bin/") #more than one ndir
template+=("/usr/include/")
template+=("/usr/lib/")
template+=("/usr/lib32/")
template+=("/usr/lib64/")
template+=("/usr/local")
template+=("/usr/share/")
template+=("/usr/src/")
template+=("/usr/")
template+=("/var/lib/")
template+=("/var/local/")
template+=("/var/opt/")
template+=("/var/run/")
template+=("/var/tmp/")
template+=("/var/")

for element in "${template[@]}"; do 
    result=$( echo "$BASEDIR" | grep -o "^$element")
    
        #It is /home/guest/systemdir/
    if [ "$result" != "" ]; then
    

        d=$( echo "${result}" | awk -F '/' '{print NF-1}') #get the depth of the match
        echo $d #return the depth
	    break

        # Notes
        #newdir=$( echo "${BASEDIR}" | sed -E 's/(^([^/]*[/]){5}).*/\1/')      #Return field 4     /home/guest/Downloads/Rootdirectory
        
    #Its is not in a preset or system directory
    #
    else
        echo ""
    fi

done	

	
#It is /home/guest/systemdir/
#if [ "$result" != "" ]; then




#	newdir=$( echo "${BASEDIR}" | sed -E 's/(^([^/]*[/]){5}).*/\1/')      #Return field 4     /home/guest/Downloads/Rootdirectory
	
	
	#We can now return the rootdir
#	echo "${newdir}"

#Its not /home/guest/systemdir/ 
#Is it the user dir? /home/guest/
#else

	#/usr/local/      add anymore system directories
	#
	#
#	result=$( echo "$BASEDIR" | grep "^/home/"$USR"/\|^/usr/local/")
	
	
#	if [ "$result" != "" ]; then
	
		#General note: If the field is less than 3 that means the files were dumped into  /home/guest      or  /usr/local/ meaning there is no root folder
		#    																			We could exclude the other newly created directories surrounding the files
		#																			by time exclusion. The first file and last file modified times
		#																		Output to log  time exclusion files ---->  these folders were ommited from filtered items due to time difference
	
		
#		newdir=$( echo "${BASEDIR}" | sed -E 's/(^([^/]*[/]){4}).*/\1/')      #Return field 3      /home/guest/Rootdirectory
		#We can now return the rootdir
#		echo "${newdir}"
#	else
#		echo ""
#	fi
#fi
	
	# We know that the root is garuanteed to be these if it is here.
	#/home/guest/
	#/usr/local/
}


# append statistics and return total time between two files
gettime() {
local SRTTIME
local FINTIME
local s
local f
local ENDTM
local RANGE
local PRD
local ST
local FN


# Calculate the range from two dates including Day and time
SRTTIME=$( head -n1 $SORTCOMPLETE | awk '{print $1 " " $2}')  #the TIME with DAY
s=$( echo $(date -d "$SRTTIME" "+%s"))   # convert to epoch so we can add subtract

RANGE=$(( s + argone ))  # End time range based on search criteria 
if [ "$THETIME" == "noarguser" ]; then
	RANGE=$(( s + 300 ))
fi

# convert back to YYYY MM-DD HH:MM:SS
PRD=$( echo $(date -d "@$RANGE" +'%Y-%m-%d %H:%M:%S'))
# get the last time on the list
FINTIME=$( awk -F" " -v tme="$PRD" '$0 < tme' $1 | sort -sr | head -n 1 | awk -F ' ' '{print $1 " " $2}')  
f=$( echo $(date -d "$FINTIME" "+%s"))
FN=$( date -d "$FINTIME" +"%T")

# get the difference
DIFFTIME=$(( f - s )) 
#Rearrange format for log file
# We only want to show HH:MM:SS
ENDTM=$(date -d "@$DIFFTIME" -u +'%H:%M:%S')  #utc time
#ST=$( head -n1 $1 | awk '{print $2}')         #The TIME


#Account for SRC
ST=$( head -n1 $1 | awk '{print $1 " " $2}')  #the TIME with DAY
sSRC=$( date -d "$ST" "+%s")     
fSRC=$( date -d "$FINTIME" +"%s")
eSRC=$(( fSRC - sSRC ))
srcE=$(date -d "@$eSRC" -u +'%H:%M:%S')

# Check if there is only 1 file or both are same tim
time_str=$ENDTM e
threshold=$tm  
IFS=":" read -r hh mm ss <<< "$time_str"
total_seconds=$((10#$hh * 3600 + 10#$mm * 60 + 10#$ss)) # base 10
if (( DIFFTIME == 0 )) || (( total_seconds > threshold )); then #if [ "$DIFFTIME" == "0" ]; then
	ENDTM=$ENDTM" file(s) created at: "$SRTTIME   
fi

echo >> $2
echo >> $2
if [ "$THETIME" == "noarguser" ]; then
	echo "Specified: "$argone "minutes" >> $2
else
	echo "Specified: "$argone "seconds" >> $2
fi
echo >> $2
echo "Batch analysis and stats:" >> $2
echo -e $ST" Start" >> $2
echo -e $FN" Finish" >> $2
echo -e $srcE" Compile time" >> $2
echo "${ENDTM}"
}

# get random number
getrnd() { local tokenID=$RANDOM; rndNO="${tokenID:0:3}"; echo $rndNO; }
