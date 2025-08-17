#!/bin/bash
#
#      recentchanges search             Developer Buddy v3.0    08/04/2025
#
# If some as root calls the program with 2 arguments thats not intended use so exit
# we would fail to get our correct username such as they put a second bogus argument
. /usr/share/porteus/porteus-functions
get_colors
. /usr/local/save-changesnew/comp
. /usr/local/save-changesnew/rntchangesfunctions
if [ `whoami` != "root" ]; then # This script requires 4 variables  $1 search  $2 thetime or notime  $3 theusername  $4 PWD
	echo "Please enter your root password below"
    su - -c "/usr/local/save-changesnew/recentchangessearch.sh $1 '$2' $3 '$4'"
    exit
fi
USR=$3
if [ "$USR" == "" ]; then echo please call from recentchanges; exit; fi
if [ "$4" == "" ]; then echo "incorrect usage please call from recentchanges"; exit 1; fi
if [ "$1" != "search" ]; then echo exiting not a search && exit; fi
clearlogs() { #called for two diff searched flt or unflt
    rm $( echo $MODULENAME"xSystemDiffFromLastSearch" | sed "s|^/||g")* 2> /dev/null #Clear all old diff logs
    rm $( echo $MODULENAME"xFltDiffFromLastSearch" | sed "s|^/||g")* 2> /dev/null 
    rm $( echo $MODULENAME"xFltchanges" | sed "s|^/||g")* 2> /dev/null  #Clear all old searches
    rm $( echo $MODULENAME"xFltTmp" | sed "s|^/||g")* 2> /dev/null 
    rm $( echo $MODULENAME"xSystemchanges" | sed "s|^/||g")* 2> /dev/nul
    rm $( echo $MODULENAME"xSystemTmp" | sed "s|^/||g")* 2> /dev/null 
	rm $( echo $MODULENAME"xNewerThan" | sed "s|^/||g")* 2> /dev/null
	rm $( echo $MODULENAME"xDiffFromLast_" | sed "s|^/||g")* 2> /dev/null  #rm $( echo $MODULENAME"xNewerThan" | sed "s|^/||g")* 2> /dev/null
}
work=work$$												                    ;		tmp=/tmp/work$$			
FLBRAND=`date +"MDY_%m-%d-%y-TIME_%R_%S"|tr ':' '_'`	;		RECENTNUL=$tmp/list_recentchanges_filterednul.txt						 
BRAND=`date +"MDY_%m-%d-%y-TIME_%R"|tr ':' '_'`		    ; 		chxzm=/rntfiles.xzm
UPDATE=$tmp/save.transferlog.tmp						            ; 		RECENT=$tmp/list_recentchanges_filtered.txt
COMPLETE=$tmp/list_complete.txt							            ;		SORTCOMPLETE=$tmp/list_complete_sorted.txt
COMPLETENUL=$tmp/list_completenul.txt							;		toutnul=$atmp/toutputnul.tmp
TMPCOMPLETE=$tmp/tmp_complete.txt						        ; 		ABSENT=$tmp/absent.txt
TMPOUTPUT=$tmp/list_tmp_sorted.txt						        ;       USRDIR=/home/$USR/Downloads
dr=/usr/local/save-changesnew											;       logpst=$dr/logs.gpg #Version 3
flth=$dr/flth.csv																	;       statpst=$dr/stats.gpg          
atmp=/tmp/atmp$$															;       rout=$atmp/routput.tmp 
xdata=$atmp/logs_stat.log													;       tout=$atmp/toutput.tmp 
TMPOPT=$tmp/tmp_holding												;		xdata2=$atmp/logs_log.log
slog=/tmp/scr
diffrlt="false"											                        ;		nodiff="false"
validrlt="false"										                            ;		flsrh="false"
mkdir $tmp																	
mkdir $atmp
if [ "$ANALYTICSECT" == "true" ]; then start=$(date +%s.%N); fi
if [ "$STATPST" == "true" ]; then
    if [ -f $logpst ]; then
        sz=$( stat -c %s "$logpst")
        if [ $(( sz / 1048576 )) -gt $logSIZE ]; then
            if [ "$logPRF" == "del" ]; then
                : > $logpst
            elif [ "$logPRF" == "stop" ]; then
                cyan "persist log saving stopped on size limit"
            fi
            STATPST="false"
            if [ "$logPRF" == "rfh" ]; then
                rm $logpst
                STATPST="true"
            fi
		elif [ $(( sz / 1048576 )) -ge $compLVL ]; then
	    	nc="--compress-level 0" #disable compression
        elif [ $sz -eq 0 ]; then
            cyan "$logpst is 0 bytes. to resume persistent logging delete file"
            STATPST="false"
        fi
    fi
fi

# If a desired time is specified we will search for that  (in seconds)
if [ "$2" != "noarguser" ] && [ "$2" != "" ]; then
 	# is it a number
	if [ "$2" -ge 0 ] 2>/dev/null; then
    
        argone=$2 #What the user passed
        comp $argone
        tmn=$qtn
		cyan "searching for files $2 seconds old or newer"  
								   
    else
        # we dont want the log file to become a .tar.gz for example
        argone=".txt"    
    	test -d "${4}" && cd "${4}" || { echo "Invalid argument ${4} . PWD required."; exit 1; }
  
    	filename=$2
    	#echo this is filename $filename
    	#rlDIR="false"
		
		#if [[ $filename = *[[:space:]]* ]]; then
			#theDIR=$( echo $2 | sed 's/ /\\ /g')
			#filename="$theDIR"
			#echo $theDIR
		
			#echo has a space!!
		#fi
		
    	test -f "${filename}" || { test -d "${filename}" || echo no such directory file or integer; exit 1; }
    	parseflnm=$(echo $2 | sed 's@.*/@@')         # filename
 
    	# sed -e 's![^/]*$!!'   this will take /mydir/thisdir/myfile.txt and return     /mydir/myfile/
    	# sed -e 's/\/$//')  this will   take  /mydir/thisdir/myfile.txt and return   	/myfile.txt
    	# sed sed -e 's@.*/@@' this will take /myfile.txt and return 					myfile.txt
    	if [ "$parseflnm" == "" ]; then
    		parseflnm=$(echo $2 | sed -e 's/\/$//' -e 's@.*/@@')  # user selected a directory so we have to reparse
    	fi

    	cyan "searching for files newer than $filename "

    	flsrh="true"
    	FEEDFILE=$RECENTNUL	
        if [ "$FEEDBACK" != "true" ]; then
       	    find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var -newer "$filename" -not -type d -print0 2> /dev/null | tee $RECENTNUL > /dev/null 2> /dev/null
        else
            find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var -newer "$filename" -not -type d -print0 | tee "$RECENTNUL" 2>/dev/null #Show terminal output FEEDBACK
        fi #cp $COMPLETE $RECENT	#we need two files one to work with and one to add customized time for user reading due to output supression above                     	
    fi
else # Search the default time  5 minutes.
	argone="5"
	tmn=$argone
			
    cyan "searching for files 5 minutes old or newer"
fi 

if [ "$tmn" != "" ]; then # The search is for system files
	logf="$RECENT" 
    FEEDFILE=$COMPLETENUL
    if [ "$FEEDBACK" != "true" ]; then
	    find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var -mmin -"$tmn" -not -type d -print0 2> /dev/null | tee $COMPLETENUL > /dev/null 2> /dev/null
		find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var \( -cmin -"$tmn" -o -amin -"$tmn" \) -not -type d -print0 2> /dev/null | tee "$toutnul" > /dev/null 2> /dev/null            # This cannot be fed into $FEEDFILE ******
    else
        find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var -mmin -"$tmn" -not -type d -print0 | tee "$COMPLETENUL" 2>/dev/null 
		find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var \( -cmin -"$tmn" -o -amin -"$tmn" \) -not -type d -print0 | tee "$toutnul" 2> /dev/null
    fi
	#cp $RECENT $COMPLETE	#we need two files one to work with and one to add customized time for user reading
                         	#due to output supression above we do it this way    |tee $file1 $file2 > /dev/null doesnt work               
fi
if [ "$checkSUM" == "true" ]; then cyan "Running checksum."; fi
if [ "$ANALYTICSECT" == "true" ]; then 
	end=$(date +%s.%N)
	if [ "$checkSUM" == "true" ]; then 
		  cstart=$(date +%s.%N)
	fi 
fi
#read -r -p "Press Enter to continue..."
#exit

###New to version3
# We are making a comparison. Non the less we are working with \0 terminated    <--------
while IFS= read -r -d '' f; do
		f="${f//$'\n'/\\n}"
		echo "$f"
done < $FEEDFILE >> $xdata        # Our main list  with \n escaped to \\n  so we can compare here and also further down
while IFS= read -r -d '' f; do
		f="${f//$'\n'/\\n}"
		echo "$f"
done < $toutnul >> $tout 						# Tempory Secondary list ..   for comparison

if [ -s $tout ]; then grep -Fxv -f $xdata $tout > $TMPCOMPLETE; fi
>$tout
if [ -s $TMPCOMPLETE ]; then
	while IFS= read -r x; do x="${x//$'\\n'/\n}" ; printf '%s\0' "$x"; done < $TMPCOMPLETE > $xdata     # convert back to \n  and \0 for copying
	# Slackpkg and pacman download detection ect
	# We have to store the access time ******   and/or  checksum if enabled
	#
	# We are appending the results of this after our original loop. Just so these new files are shown.
	# what we do with the data can be extensive but only need to process it if checksum is enabled.
	#
	# Efficiency gains are massive with xargs so running this includes those minute files that arent shown and even that is fast
	# So we are able to bring even more detection that way if the user wants to run in Diagnostic mode.
	#
	# While loop more reliable than xargs capture all stats in one go
	if [ "$mMODE" == "normal" ]; then
		while IFS= read -r -d '' x; do
			adtcmd=""
			fs=""
			output=""
			y="${x//$'\n'/\\n}"
			if [ -e "$x" ] && [ -f "$x" ]; then
				stat_output=$(stat -c "%Y %X %Z %i" "$x") # Get modified access time change time and inode number
				read mtime atime itime i <<< "$stat_output"
				ct=$(date -d "@$itime" +"%Y-%m-%d %H:%M:%S")
				at=$(date -d "@$atime" +"%Y-%m-%d %H:%M:%S") #mdate=$(date -d "@$mtime" +"%Y-%m-%d %H:%M:%S")
				if [ -n "$ct" ]; then # This at least ensures the format is correct with a date
					if (( itime > mtime )); then
						if [ "$checkSUM" == "true" ]; then
							csum=$(md5sum "$x" | awk '{print $1}')
							fs=$(stat --format=%s "$x") 
							adtcmd="$csum $fs"
						fi
						if [ -n "$ct" ] && [ -n "$at" ]; then # This is critical we want to ensure the best possible chance of proper format exclude everything else
							output="$ct \"$y\" $i $at $adtcmd"
							printf '%s\n' "$output" >> $tout
						fi
					fi
				fi
			else
				printf 'NOTA-FI-LE 77:77:77 "%s"\n' "$y" >> $tout
				printf 'Nosuchfile,,"%s"\n' "$y" >> $TMPOPT
			fi
		done < $xdata
	elif [ "$mMODE" == "mem" ]; then
		declare -a ffile
		declare -a nsf
		while IFS= read -r -d '' x; do
			adtcmd=""
			output=""
			fs=""
			y="${x//$'\n'/\\n}"
			if [ -e "$x" ] && [ -f "$x" ]; then
				stat_output=$(stat -c "%Y %X %Z %i" "$x")
				read mtime atime itime i <<< "$stat_output"
				ct=$(date -d "@$itime" +"%Y-%m-%d %H:%M:%S")
				at=$(date -d "@$atime" +"%Y-%m-%d %H:%M:%S")
				if [ -n "$ct" ]; then
					if (( itime > mtime )); then
						if [ "$checkSUM" == "true" ]; then
							csum=$(md5sum "$x" | awk '{print $1}')
							fs=$(stat --format=%s "$x") 
							adtcmd="$csum $fs"
						fi
						if [ -n "$ct" ] && [ -n "$at" ]; then
							output="$ct \"$y\" $i $at $adtcmd"
						    ffile+=("$output")
						fi
					fi
				fi
			else
				ffile+=("NOTA-FI-LE 77:77:77 \"$y\"")
				nsf+=("Nosuchfile,,\"$y\"")
			fi
		done < $xdata
		unset IFS
	elif [ "$mMODE" == "mc" ]; then # Single core these files are few. Mainloop is parallel
	    xargs -0 -I{} /usr/local/save-changesnew/searchfiles "{}" "$atmp" "$checkSUM" < $xdata
		if compgen -G "$atmp/searchfiles1_*_tmp.log" > /dev/null; then cat "$atmp"/searchfiles1_*_tmp.log >> "$tout"; fi
		if compgen -G "$atmp/searchfiles2_*_tmp.log" > /dev/null; then cat "$atmp"/searchfiles2_*_tmp.log > "$TMPOPT"; fi
	else
		echo incorrect mMODE && exit
	fi # $tout is merged into $SORTCOMPLETE after main loop below
fi
rm $xdata
###End New to version 3

#We have a log of all system changes $COMPLETE will include that

#parse stat modified time
#stat -c '%y' "$x" | sed -e 's/\...........-....//g'     Actual time then shave off with sed some random stuff on the side
#date -d @1234567890 +'%Y-%m-%d %H:%M:%S'       <-------- convert epoch seconds to time and then rearrange format
#We will be using epoch
#Lets add file modified time so it can be easily viewed and replace $COMPLETE with $SORTCOMPLETE
#Files are copied lets take our time and check for bogus files on the right  ie cache items                                                                                             
																																																																						#NOT-AFILE is useful info
#while IFS= read x; do test -e "$x" && { f=$(stat -c '%Y' "$x") ; echo $(date -d "@$f" +'%Y-%m-%d %H:%M:%S') "$x"; } >> $SORTCOMPLETE || { echo "NOTA-FI-LE 77:77:77" "$x" >> $SORTCOMPLETE; echo "Nosuchfile,,\"${x}\"" >> $tout; }; done < $FEEDFILE 
#cp $SORTCOMPLETE $RECENT
#unset IFS

 # Main loop
 # Run capture stats in one shot more reliable than xargs    
if [ "$mMODE" == "normal" ]; then
	while IFS= read -r -d '' x; do
		adtcmd=""
		output=""
		fs=""
		y="${x//$'\n'/\\n}"
		if [ -e "$x" ] && [ -f "$x" ]; then
			read f atime i <<<$(stat -c "%Y %X %i" "$x")
			mt=$(date -d "@$f" +"%Y-%m-%d %H:%M:%S")
			ats=$(date -d "@$atime" +"%Y-%m-%d %H:%M:%S")
			if [ -n "$mt" ]; then
					if [ "$checkSUM" == "true" ]; then
						csum=$(md5sum "$x" | awk '{print $1}')
						fs=$(stat --format=%s "$x") 
						adtcmd="$csum $fs"
					fi
				output="$mt \"$y\" $i $ats $adtcmd"
				printf '%s\n' "$output" >> $SORTCOMPLETE
			fi
		else
			printf 'NOTA-FI-LE 77:77:77 "%s"\n' "$y" >> $SORTCOMPLETE
			printf 'Nosuchfile,,"%s"\n' "$y" >> $TMPOPT
		fi
	done < $FEEDFILE
	unset IFS
elif [ "$mMODE" == "mem" ]; then
	while IFS= read -r -d '' x; do
		adtcmd=""
		output=""
		fs=""
		y="${x//$'\n'/\\n}"
		if [ -e "$x" ] && [ -f "$x" ]; then
			read f atime i <<<$(stat -c "%Y %X %i" "$x")
			mt=$(date -d "@$f" +"%Y-%m-%d %H:%M:%S")
			ats=$(date -d "@$atime" +"%Y-%m-%d %H:%M:%S")

			if [ -n "$mt" ]; then  # This at least ensures the format is correct if there is no date
				if [ "$checkSUM" == "true" ]; then
					csum=$(md5sum "$x" | awk '{print $1}')
					fs=$(stat --format=%s "$x") 
					adtcmd="$csum $fs"
				fi
				output="$mt \"$y\" $i $ats $adtcmd"
				ffile+=("$output")
			fi
		else
			ffile+=("NOTA-FI-LE 77:77:77 \"$y\"")
			nsf+=("Nosuchfile,,\"$y\"")
		fi
	done < $FEEDFILE
	unset IFS
	printf "%s\n" "${ffile[@]}" >> $SORTCOMPLETE
	if [ ${#nsf[@]} -gt 0 ]; then printf "%s\n" "${nsf[@]}" > $COMPLETE; fi
elif [ "$mMODE" == "mc" ]; then # parallel search
	#xargs -0 -I{} -P4 /usr/local/save-changesnew/mainloop "{}" $atmp $checkSUM < $FEEDFILE
	xargs -0 -n8 -P4 /usr/local/save-changesnew/mainloop "$atmp" "$checkSUM" < $FEEDFILE
	if compgen -G "$atmp/mainloop1_*_tmp.log" > /dev/null; then cat "$atmp"/mainloop1_*_tmp.log > "$SORTCOMPLETE"; fi
	if compgen -G "$atmp/mainloop2_*_tmp.log" > /dev/null; then cat "$atmp"/mainloop2_*_tmp.log > "$COMPLETE"; fi
fi
# Main loop we append to it below from our top loop # 
if [ "$ANALYTICSECT" == "true" ]; then cend=$(date +%s.%N); fi
if [ -s $TMPOPT ]; then cat $TMPOPT >> $COMPLETE; fi  # $COMPLETE has stats that are saved to  $statpst

#tr '\0' '\n' < $FEEDFILE > $xdata && mv $xdata $FEEDFILE        # This file is important. Keep it in \n format
# rm $FEEDFILE

# Lose the quotes
#awk -F'"' '{print $2}' $TMPCOMPLETE >> $SORTCOMPLETE        this will grab whatever is inside the quotes

#Regarding cache items that do not exist this is leading to what I call the segway of recentchanges we can call other functions and methods
#
#We can inform the user that there are files ie empty sym links or their filters are capturing .cache or cache items. Inform rather than do will always be rule #1
#
#
#Now we could export a file with all filters used from this script but instead lets lead to our segway
#
#we build in detection   your compiled files where at this time. well at this time a folder was made in   /etc/  by your compiler. 
#so we output a file rntfilesSuggestions       warn you should adjust your filter to  remove    /etc   filter
#
#we then package those files in /etc  and send it to   rntfilesMissed.xzm  with no archive.   the user can decide to extract the .xzm and grab that one missing folder out of there
#
#

# if there are results seperate /tmp out so not confusing  ie unnessesary files in system log
# send the /tmp to a seperate log
if [ -s $SORTCOMPLETE ]; then
	# New to version 3 appending unq ctime files regarding slackpkg pacman
	sort -u -o  $SORTCOMPLETE $SORTCOMPLETE      # Original  -o       version 3   -u -o
	SRTTIME=$( head -n1 $SORTCOMPLETE | awk '{print $1 " " $2}')  # day and time
	PRD=$SRTTIME
	
	if [ -s $tout ]; then  #   We dont want anything before our main files.

		grep -v 'NOTA-FI-LE 77:77:77' "$tout" | awk -v tme="$PRD" '{ ts = $1 " " $2; if (ts >= tme) print }' > $TMPOPT ; cat $TMPOPT >> $SORTCOMPLETE
	fi   
	#
	##
	# At this point we have to filter out files from the future cache files ect
	if [ "$flsrh" != "true" ]; then
		
		s=$( echo $(date -d "$SRTTIME" "+%s"))  
		if [ "$2" == "noarguser" ]; then         # Also if its noarguser         We know its 300 seconds
			RANGE=$(( s + 300 ))
		else
			#if [ "$2" -ge 0 ] 2>/dev/null; then      #   seconds
				RANGE=$(( s + argone ))  # End time range based on search criteria 
			#fi
		fi
		PRD=$(date -d "@$RANGE" +'%Y-%m-%d %H:%M:%S') # convert back to YYYY MM-DD HH:MM:SS
		grep -v 'NOTA-FI-LE 77:77:77' "$SORTCOMPLETE" | awk -v tme="$PRD" '{ ts = $1 " " $2; if (ts <= tme) print }' > $tout ; mv $tout $SORTCOMPLETE
		
	fi	
	if [ "$flsrh" == "true" ]; then grep -v 'NOTA-FI-LE 77:77:77' "$SORTCOMPLETE" > $tout ; mv $tout $SORTCOMPLETE ; fi
	sort -u -o  $SORTCOMPLETE $SORTCOMPLETE
	# Human readable
	# We want a human readballe first two columns date and time and the filename without the quotes.
	awk '{print $1, $2}' $SORTCOMPLETE > $tout
	awk -F'"' '{print $2}' $SORTCOMPLETE  > $TMPCOMPLETE
	paste -d' ' $tout $TMPCOMPLETE > $TMPOPT
	sort -o $TMPOPT $TMPOPT
	cp $TMPOPT $RECENT # RECENT is unfiltered viewable
	#sed -i -E 's/^([^ ]+ [^ ]+ [^ ]+)( .*)$/\1/' $TMPOPT  # bring it to proper format    first 3 columns  doesnt work with spaces ***
	# Lose the quotes
	#sed -i 's/"//g' $TMPOPT      #  remove quotes on filename  works
	# End Human readable
	# End Version 3	


	## Removing tmp from search Specific to this script
    #Remove /tmp from system search as it can be too confusing
    cat $TMPOPT | grep ' /tmp/' > $TMPOUTPUT        # Version 3 proper format   | sed -E 's/^([^ ]+ [^ ]+ [^ ]+)( .*)$/\1/'
	sort -o $TMPOUTPUT $TMPOUTPUT   # This is viewable tmp files
	#sed -i '/[[:space:]]"\/tmp/d' "$SORTCOMPLETE" # Remove /tmp  from the main search data
	sed -i '/\"\/tmp/d' "$SORTCOMPLETE"
	sed -i '/ \/tmp/d' "$TMPOPT" # Remove /tmp  from the main search data
	sed -i '/ \/tmp/d' "$RECENT" # Remove /tmp  from the main search data
	## End Removing tmp from search
fi
#called by rnt symlink so filtered search or its a newer than file search
if [ "$5" == "filtered" ] || [ "$flsrh" == "true" ]; then 
	logf="$TMPOPT"
	if [ "$5" == "filtered" ] && [ "$flsrh" == "true" ]; then logf="$RECENT" ; fi  # We dont want to filter its inverse from rnt myfile
	# Our search criteria is only filtered items therefor logf has to be $TMPOPT

    /usr/local/save-changesnew/filter $TMPOPT $USR # TMPOPT is filtered viewable
fi
#Filtering complete

# $SORTCOMPLETE is our system log 
# $TMPOPT is human readable and filtered from  SORTCOMPLETE
# $RECENT is human readable and unfiltered ... 
# $COMPLETE is used to save to PST storage stats

#
#	$tout is availble for a tmp file now
#	$FEEDFILE is available for tmp file     $RECENTNUL or $COMPLETENUL
# $TMPOUTPUT is availbe for tmp file
#
# 
#End of Systemchanges log
MODULENAME=${chxzm:0:9}         # Our module name
cd $USRDIR

# Set out filenames
if [ -s $SORTCOMPLETE ] ; then
	validrlt="true"
    #FILTERED
    if [ "$flsrh" == "true" ]; then
	    flnm="xNewerThan_${parseflnm}"$argone
	    flnmdff="xDiffFromLast_${parseflnm}"$argone
		clearlogs	    
		#rm $( echo $MODULENAME"xDiffFromLast_" | sed "s|^/||g")* 2> /dev/null 
		
	    test -e $USRDIR$MODULENAME"${flnm}" && { cp $USRDIR$MODULENAME"${flnm}" $tmp; } # do we have an old search to  use?  If an old search is valid we compare to our new search
	    #rm $( echo $MODULENAME"xNewerThan" | sed "s|^/||g")* 2> /dev/null
    		#rm $( echo $MODULENAME"xDiffFromLast_" | sed "s|^/||g")* 2> /dev/null 
    elif [ "$5" == "filtered" ]; then
	    flnm="xFltchanges_"$argone
	    flnmdff="xFltDiffFromLastSearch_"$argone
        test -e "$USRDIR$MODULENAME$flnm" && cp "$USRDIR$MODULENAME$flnm" $tmp
        clearlogs
        if [ -s $TMPOUTPUT ]; then # move /tmp output for user
            cp $TMPOUTPUT $USRDIR$MODULENAME"xFltTmpfiles"$argone
            chown $USR $USRDIR$MODULENAME"xFltTmpfiles"$argone
        fi

    #UNFILTERED
    else
	    flnm="xSystemchanges"$argone
	    flnmdff="xSystemDiffFromLastSearch"$argone
	    test -e $USRDIR$MODULENAME$flnm && cp $USRDIR$MODULENAME$flnm $tmp
        clearlogs
        if [ -s $TMPOUTPUT ]; then
            cp $TMPOUTPUT $USRDIR$MODULENAME"xSystemTmpfiles"$argone
            chown $USR $USRDIR$MODULENAME"xSystemTmpfiles"$argone
        fi
    fi

    difffile=$USRDIR$MODULENAME"${flnmdff}"

	# Put logic here to find old searches if stored. But enabled for recentchanges search
																																												#$SORTCOMPLETE
    test -e $tmp$MODULENAME"${flnm}" && { OLDSORTED=$tmp$MODULENAME"${flnm}" ; comm -23 "${OLDSORTED}" $logf; } > "${difffile}" && nodiff="true"
    cp $logf $USRDIR$MODULENAME"${flnm}" # viewable search to user 
    chown $USR $USRDIR$MODULENAME"${flnm}"

	#grep -q '[^[:space:]]' "${difffile}" || validrlt="false"
    if [ -s "${difffile}" ]; then
    	diffrlt="true"
    	
    	#Get the date and time of the first file in the search
    	CDATE=$( head -n1 $SORTCOMPLETE | awk '{print $1 " " $2}')  
    	#cTIME=$( head -n1 $SORTCOMPLETE | awk '{print $2}')							<---- original used only the time not time and day
    
    	#Cut out irrelevant files
        if [ "$flsrh" == "false" ]; then
        	awk -v tme="$CDATE" '$0 >= tme' "$difffile" > $TMPCOMPLETE
    	    #cat "${difffile}" | awk -F" " -v tme="$cTIME" '$2 >= tme' > $TMPCOMPLETE	<---- original "    "       as above
        else
            cat "${difffile}" > $TMPCOMPLETE 
        fi
    	echo >> "${difffile}"
    	
    	while IFS="" read -r p || [ -n "$p" ]; do
			cFILE=$( echo "$p" | cut -d " " -f3-)  # no quotes in $TMPCOMPLETE        cFILE=$(echo "$p" | awk -F'"' '{print $2}')    # Version 3  grab the filename from quotes   "   spaces in file       "
            #dt=$(echo "$p" | cut -d " " -f1-2)
			grep -Fqs "$cFILE" $SORTCOMPLETE && { echo "Modified" "$p" >> $ABSENT; echo "Modified" "$p" >> $rout; } || { echo "Deleted " "$p" >> $ABSENT; echo "Deleted" "$p" >> $rout; } # record delete for stats                 
		done < $TMPCOMPLETE
		unset IFS

		#sort -o $ABSENT $ABSENT
		test -f $ABSENT  && { echo Applicable to your search ; cat $ABSENT ; } >> "${difffile}" || { echo "None of above is applicable to search. It is the previous search"; } >> "${difffile}"

    else
        test -e "${difffile}" && rm "${difffile}"
    fi

	ofile=$atmp/tmpinfo
	tfile=$atmp/tmpd
	# TMP SRG
    if [ -d /tmp/rc ] && [ "$ANALYTICS" == "true" ] && [ "$STATPST" == "false" ]; then
        for file in /tmp/rc/*; do
            cat $file >> $ofile  2> /dev/null
        done
        if [ -s $ofile ]; then 
            sort -u -o $ofile $ofile # Built the previous search history
			cc=$(hanly $SORTCOMPLETE $ofile $5) #hybrid analysis
			if [ -n "$cc" ]; then
				if [ "$cc" == "csum" ]; then
					awk '{ print "\033[31m *** Checksum of file \033[0m" $0 "\033[31m altered without a modified time\033[0m" }' /tmp/cerr && rm /tmp/cerr #red "*** Checksum of file altered without a modified time." red "*** Checksum of file altered without a modified time."
				else
					echo "Detected $cc CPU cores."
				fi
			fi
			[[ -s $difffile ]] && [[ -n "$( tail -n 1 $difffile)" ]] && green "Hybrid analysis on"
        fi   
    fi
	# STATPST SRG
    if [ "$STATPST" == "true" ]; then 
		# hybrid analysis Only if storing persistently
		if [ "$ANALYTICS" == "false" ]; then # process the hybrid anlys
			if [ -s $logpst ]; then
				if decrypt $xdata2 $logpst; then 			
					awk 'NF' $xdata2 > $ofile # Remove spaces and built the previous search history
				     if [ -s $ofile ]; then 
				        sort -u -o $ofile $ofile 
						cc=$(hanly $SORTCOMPLETE $ofile $5) #hybrid analysis		New to version 3
						if [ -n "$cc" ]; then
							if [ "$cc" == "csum" ]; then
								awk '{ print "\033[31m *** Checksum of file \033[0m" $0 "\033[31m altered without a modified time\033[0m" }' /tmp/cerr && rm /tmp/cerr #red "*** Checksum of file altered without a modified time."
							else
								echo "Detected $cc CPU cores."
							fi
						fi
						[[ -s $difffile ]] && [[ -n "$( tail -n 1 $difffile)" ]] && green "Hybrid analysis on"
				    fi						
				else
					echo "Failed to decrypt log file in hanalysis for STATPST"
				fi
			fi
		fi
		# Encrypt 
        if [ -s $rout ]; then
            sort -u -o $rout $rout # remove anything already in written
            sed -i -E 's/^([^ ]+) ([^ ]+ [^ ]+) (.+)$/\1,"\2","\3"/' $rout          #csv format
            #sed -i -E 's/^([^ ]+) ([^ ]+) ([^ ]+) (.+)$/\1,"\2 \3","\4"/' $rout 
            imsg=$(storeenc $rout $statpst) # save and encrypt statpst log    func appends COMPLETE    Nosuchfile good info
            ret=$?
            if [ $ret -ne 0 ]; then
                echo "$imsg"
            else
                if [ "$imsg" != "" ]; then green "Persistent stats created."; imsg=""; fi
            fi
        fi
        imsg=$(storeenc $SORTCOMPLETE $logpst "dcr") # save and encrypt main log
        ret=$?
        if [ $ret -ne 0 ]; then
            echo "$imsg"
        else
            if [ "$imsg" -ge 0 ] 2>/dev/null; then 
                if (( imsg % 10 == 0 )); then  cyan "$imsg searches in gpg log"; fi # only output every 10 incriments
            elif [ "$imsg" != "" ]; then
                green "Persistent search log file created." # only... creation
            fi
        fi
    fi # End STATPST
	[ -s "$slog" ] && { [ "$cdiag" == "false" ] && cat $slog || echo >> "$difffile" && cat $slog >> "$difffile"; } 
	test -f $slog && rm $slog
    test -f $rout && rm $rout # incase pst off
    filterhits $RECENT $flth # store stats     pass a clean complete list so regex doesnt break
    postop $logf $6 # run post op scripts  ie file doctrine  POSTOP var           IF this is a filtered search or new than file search we do post ops on those specific files
	test -e "$difffile" && chown $USR "$difffile"
fi 
if [ "$ANALYTICS" == "true" ] && [ "$STATPST" == "false" ] ; then 
    stmp $SORTCOMPLETE # save log to /tmp
    if [ ! -f /tmp/rc/full ]; then cyan "Search saved in /tmp"; fi # save in /tmp but make notification go away after full 
fi # Logging complete
rm -rf $tmp #cleanup
rm -rf $atmp
if [ "$ANALYTICSECT" == "true" ]; then
    el=$(awk "BEGIN {print $end - $start}")
    printf "Search took %.3f seconds.\n" "$el"
	if [ "$checkSUM" == "true" ]; then
		el=$(awk "BEGIN {print $cend - $cstart}")
		printf "Checksum took %.3f seconds.\n" "$el"
	fi
fi
if [ "$flsrh" == "true" ]; then
    cyan "All files newer than ""${filename}""  in /Downloads"
    echo
elif [ "$5" == "filtered" ]; then
    cyan "All new filtered files are listed in /Downloads"
else 						   			         		
  	cyan "All new system files are listed  in /Downloads"
  	echo
fi
if [ "$nodiff" == "true" ] && [ "$diffrlt" == "false" ]; then
    green "There was no difference file. That is the results themselves are true."
fi
if [ "$validrlt" == "false" ]; then
	green  "No new files to report."
	echo
fi
