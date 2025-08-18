#!/bin/bash
#      recentchanges search             Developer Buddy v3.0    08/14/2025
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
#set -o pipefail
#set -x +x
work=work$$												                    	;		tmp=/tmp/work$$		
FLBRAND=`date +"MDY_%m-%d-%y-TIME_%R_%S"|tr ':' '_'`		;		ABSENT=$tmp/absent.txt	
BRAND=`date +"MDY_%m-%d-%y-TIME_%R"|tr ':' '_'`				;		chxzm=/rntfiles.xzm
USRDIR=/home/$USR/Downloads											;		RECENT=$tmp/list_recentchanges_filtered.txt
UPDATE=$tmp/save.transferlog.tmp		    							; 		RECENTNUL=$tmp/list_recentchanges_filterednul.txt
COMPLETE=$tmp/list_complete.txt							           		; 		SORTCOMPLETE=$tmp/list_complete_sorted.txt
COMPLETENUL=$tmp/list_completenul.txt							    ;		toutnul=$atmp/toutputnul.tmp
TMPCOMPLETE=$tmp/tmp_complete.txt									;		dr=/usr/local/save-changesnew
TMPOUTPUT=$tmp/list_tmp_sorted.txt						       		; 		rout=$atmp/routput.tmp 
flth=$dr/flth.csv						       											;       tout=$atmp/toutput.tmp          																				
atmp=/tmp/atmp$$																;     	xdata=$atmp/logs_stat.log	
TMPOPT=$tmp/tmp_holding													;       xdata2=$atmp/logs_log.log					
slog=/tmp/scr																		;     	pydb=/usr/local/save-changesnew/recent.db		  
pytmp=$atmp/pytmp.tmp 														;     	pydbpst=/usr/local/save-changesnew/recent.gpg	
statpst=$dr/stats.gpg 															;		logpst=$dr/logs.gpg 																				 																		
diffrlt="false"											                        	;		nodiff="false"
validrlt="false"										                           		;		flsrh="false"
pstc="false"																			;		dbc="false"
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
	    	nc="true" #disable compression
        elif [ $sz -eq 0 ]; then
            cyan "$logpst is 0 bytes. to resume persistent logging delete file"
            STATPST="false"
        fi
    fi
fi
if [ "$2" != "noarguser" ] && [ "$2" != "" ]; then # If a desired time is specified we will search for that  (in seconds)
	if [ "$2" -ge 0 ] 2>/dev/null; then # is it a number
        argone=$2 #What the user passed
        comp $argone
        tmn=$qtn
		cyan "searching for files $2 seconds old or newer"  					   
    else
        # we dont want the log file to become a .tar.gz for example
        argone=".txt"
    	test -d "${4}" && cd "${4}" || { echo "Invalid argument ${4} . PWD required."; exit 1; }
    	filename="$2"

    	test -f "${filename}" || { test -d "${filename}" || echo no such directory file or integer; exit 1; }
    	parseflnm=$(echo $2 | sed 's@.*/@@')         # filename
    	# sed -e 's![^/]*$!!'   this will take /mydir/thisdir/myfile.txt and return     /mydir/myfile/
    	# sed -e 's/\/$//')  this will   take  /mydir/thisdir/myfile.txt and return   	/myfile.txt
    	# sed sed -e 's@.*/@@' this will take /myfile.txt and return 					myfile.txt
    	if [ "$parseflnm" == "" ]; then
    		parseflnm="$(echo "$2" | sed -e 's/\/$//' -e 's@.*/@@')"  # user selected a directory so we have to reparse
    	fi
    	cyan "searching for files newer than $filename "
    	flsrh="true"
    	FEEDFILE=$RECENTNUL	
		fc="find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var -newer \"$filename\" -not -type d -print0"
        if [ "$FEEDBACK" != "true" ]; then eval "$fc" 2> /dev/null | tee $RECENTNUL > /dev/null 2> /dev/null ; else eval "$fc" | tee $RECENTNUL 2>/dev/null ;  fi # adjust FEEDBACK
    fi
else # Search the default time  5 minutes.
	argone="5" ; tmn=$argone
    cyan "searching for files 5 minutes old or newer"
fi 
if [ "$tmn" != "" ]; then # The search is for system files
	logf="$RECENT" 
    FEEDFILE=$COMPLETENUL
	fc="find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var -mmin -${tmn} -not -type d -print0 "
	fca="find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var \( -cmin -${tmn} -o -amin -${tmn} \) -not -type d -print0 "
    if [ "$FEEDBACK" != "true" ]; then eval "$fc" 2> /dev/null | tee $COMPLETENUL > /dev/null 2> /dev/null ; $fca 2> /dev/null | tee $toutnul > /dev/null 2> /dev/null ;  else eval "$fc" | tee $COMPLETENUL 2>/dev/null ; $fca | tee $toutnul 2> /dev/null ; fi # ..        
fi
if [ "$checkSUM" == "true" ]; then cyan "Running checksum."; fi
if [ "$ANALYTICSECT" == "true" ]; then 
	end=$(date +%s.%N)
	if [ "$checkSUM" == "true" ]; then 
		  cstart=$(date +%s.%N)
	fi 
fi #read -r -p "Press Enter to continue..."
# Slackpkg and pacman download detection ect
>$tout
while IFS= read -r -d '' f; do f="${f//$'\n'/\\n}" ; echo "$f" ; done < $FEEDFILE >> $xdata
while IFS= read -r -d '' f; do f="${f//$'\n'/\\n}" ; echo "$f" ; done < $toutnul >> $tout # Tempory Secondary list ..   for comparison
if [ -s $tout ]; then grep -Fxv -f $xdata $tout > $TMPCOMPLETE; >$tout; fi
if [ -s $TMPCOMPLETE ]; then
	while IFS= read -r x; do x="${x//$'\\n'/\n}" ; printf '%s\0' "$x"; done < $TMPCOMPLETE > $xdata     # convert back to \n  and \0 for copying
	if [ "$mMODE" == "normal" ]; then
		search $xdata $tout $COMPLETE # $tout is merged into $SORTCOMPLETE after main loop below
	elif [ "$mMODE" == "mem" ]; then
		declare -a ffile
		declare -a nsf
		searcharr $xdata 
	elif [ "$mMODE" == "mc" ]; then # Single core these files are few. Mainloop is parallel
	    xargs -0 -I{} /usr/local/save-changesnew/searchfiles "{}" "$atmp" "$checkSUM" < $xdata
		if compgen -G "$atmp/searchfiles1_*_tmp.log" > /dev/null; then cat "$atmp"/searchfiles1_*_tmp.log > $tout; fi
		if compgen -G "$atmp/searchfiles2_*_tmp.log" > /dev/null; then cat "$atmp"/searchfiles2_*_tmp.log > $COMPLETE; fi
	else
		echo incorrect mMODE && exit
	fi 
fi
rm $xdata
# Main loop                                                                        																																																																
if [ "$mMODE" == "normal" ]; then 
	search $FEEDFILE $SORTCOMPLETE $COMPLETE  # traditional loop
elif [ "$mMODE" == "mem" ]; then
	searcharr $FEEDFILE
	printf "%s\n" "${ffile[@]}" >> $SORTCOMPLETE
	if [ ${#nsf[@]} -gt 0 ]; then printf "%s\n" "${nsf[@]}" > $COMPLETE; fi
elif [ "$mMODE" == "mc" ]; then # parallel search
	#xargs -0 -I{} -P4 /usr/local/save-changesnew/mainloop "{}" $atmp $checkSUM < $FEEDFILE
	xargs -0 -n8 -P4 /usr/local/save-changesnew/mainloop "$atmp" "$checkSUM" < $FEEDFILE # no improvement beyond 4
	if compgen -G "$atmp/mainloop1_*_tmp.log" > /dev/null; then cat "$atmp"/mainloop1_*_tmp.log > $SORTCOMPLETE; fi
	if compgen -G "$atmp/mainloop2_*_tmp.log" > /dev/null; then cat "$atmp"/mainloop2_*_tmp.log >> $COMPLETE; fi
fi
if [ "$ANALYTICSECT" == "true" ]; then cend=$(date +%s.%N); fi
# Lose the quotes
#awk -F'"' '{print $2}' $TMPCOMPLETE >> $SORTCOMPLETE        this will grab whatever is inside the quotes
# if there are results seperate /tmp out so not confusing  ie unnessesary files in system log
if [ -s $SORTCOMPLETE ]; then
	# New to version 3 appending unq ctime files regarding slackpkg pacman
	sort -u -o  $SORTCOMPLETE $SORTCOMPLETE      # Original  -o       version 3   -u -o
	SRTTIME=$( head -n1 $SORTCOMPLETE | awk '{print $1 " " $2}')  # day and time
	PRD=$SRTTIME
	#
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
	sed -i '/\"\/tmp/d' $SORTCOMPLETE
	sed -i '/ \/tmp/d' $TMPOPT # Remove /tmp  from the main search data
	sed -i '/ \/tmp/d' $RECENT # Remove /tmp  from the main search data
	## End Removing tmp from search
fi
#called by rnt symlink so filtered search or its a newer than file search
if [ "$5" == "filtered" ] || [ "$flsrh" == "true" ]; then 
	logf="$TMPOPT"
	if [ "$5" == "filtered" ] && [ "$flsrh" == "true" ]; then logf=$RECENT ; fi  # We dont want to filter its inverse from rnt myfile
	# Our search criteria is only filtered items therefor logf has to be $TMPOPT
    /usr/local/save-changesnew/filter $TMPOPT $USR # TMPOPT is filtered viewable
fi
#Filtering complete
# $SORTCOMPLETE is our system log 
# $TMPOPT is human readable and filtered from  SORTCOMPLETE
# $RECENT is human readable and unfiltered ... 
# $COMPLETE is used to save to PST storage stats
#	$tout is availble for a tmp file now
#	$FEEDFILE is available for tmp file     $RECENTNUL or $COMPLETENUL
# $TMPOUTPUT is availbe for tmp file
#End of Systemchanges log
MODULENAME=${chxzm:0:9}         # Our module name
cd $USRDIR
if [ -s $SORTCOMPLETE ] ; then # Set out filenames
	validrlt="true"
    if [ "$flsrh" == "true" ]; then #FILTERED
	    flnm="xNewerThan_${parseflnm}"$argone
	    flnmdff="xDiffFromLast_${parseflnm}"$argone
		clearlogs	    
	    test -e $USRDIR$MODULENAME"${flnm}" && { cp $USRDIR$MODULENAME"${flnm}" $tmp; } # do we have an old search to  use?  If an old search is valid we compare to our new search
    elif [ "$5" == "filtered" ]; then
	    flnm="xFltchanges_"$argone
	    flnmdff="xFltDiffFromLastSearch_"$argone
        test -e "$USRDIR$MODULENAME$flnm" && cp "$USRDIR$MODULENAME$flnm" $tmp 
		[[ ! -s "$tmp$MODULENAME$flnm" ]] && test -e "/tmp/${MODULENAME}${flnm}" && cp "$/tmp${MODULENAME}${flnm}" $tmp # New we can look for old searches from recentchanges Hybrid in /tmp
        clearlogs
        if [ -s $TMPOUTPUT ]; then # move /tmp output for user
            cp $TMPOUTPUT $USRDIR$MODULENAME"xFltTmpfiles"$argone
            chown $USR $USRDIR$MODULENAME"xFltTmpfiles"$argone
        fi
    else #UNFILTERED
	    flnm="xSystemchanges"$argone
	    flnmdff="xSystemDiffFromLastSearch"$argone
	    test -e $USRDIR$MODULENAME$flnm && cp $USRDIR$MODULENAME$flnm $tmp
        clearlogs
        if [ -s $TMPOUTPUT ]; then
            cp $TMPOUTPUT $USRDIR$MODULENAME"xSystemTmpfiles"$argone
            chown $USR $USRDIR$MODULENAME"xSystemTmpfiles"$argone
        fi
    fi

    difffile=$USRDIR$MODULENAME"${flnmdff}"																																								#$SORTCOMPLETE
    test -e $tmp$MODULENAME"${flnm}" && { OLDSORTED=$tmp$MODULENAME"${flnm}" ; comm -23 "${OLDSORTED}" $logf; } > "${difffile}" && nodiff="true"
    cp $logf $USRDIR$MODULENAME"${flnm}" # viewable search to user 
    chown $USR $USRDIR$MODULENAME"${flnm}"

    if [ -s "${difffile}" ]; then #grep -q '[^[:space:]]' "${difffile}" || validrlt="false"
    	diffrlt="true"
    	CDATE=$( head -n1 $SORTCOMPLETE | awk '{print $1 " " $2}')   #Get the date and time of the first file in the search
    	#Cut out irrelevant files
        if [ "$flsrh" == "false" ]; then
        	awk -v tme="$CDATE" '$0 >= tme' "$difffile" > $TMPCOMPLETE
    	    #cat "${difffile}" | awk -F" " -v tme="$cTIME" '$2 >= tme' > $TMPCOMPLETE	<---- original "    "       as above
        else
            cat "${difffile}" > $TMPCOMPLETE 
        fi
    	echo >> "${difffile}"
    	
    	while IFS="" read -r p || [ -n "$p" ]; do
			cFILE="$( echo "$p" | cut -d " " -f3-)"  # no quotes in $TMPCOMPLETE        cFILE=$(echo "$p" | awk -F'"' '{print $2}')    # Version 3  grab the filename from quotes   "   spaces in file       "
            #dt=$(echo "$p" | cut -d " " -f1-2)
			grep -Fqs "$cFILE" $SORTCOMPLETE && { echo "Modified" "$p" >> $ABSENT; echo "Modified" "$p" >> $rout; } || { echo "Deleted " "$p" >> $ABSENT; echo "Deleted" "$p" >> $rout; } # record delete for stats                 
		done < $TMPCOMPLETE
		unset IFS
		test -f $ABSENT  && { echo Applicable to your search ; cat $ABSENT ; } >> "${difffile}" || { echo "None of above is applicable to search. It is the previous search"; } >> "${difffile}"

    else
        test -e "${difffile}" && rm "${difffile}"
    fi
	ofile=$atmp/tmpinfo
	tfile=$atmp/tmpd
    if [ -d /tmp/rc ] && [ "$ANALYTICS" == "true" ] && [ "$STATPST" == "false" ]; then # TMP SRG
        for file in /tmp/rc/*; do
            cat $file >> $ofile  2> /dev/null
        done
        if [ -s $ofile ]; then 
            sort -u -o $ofile $ofile # Built the previous search history
			cc=$(hanly $SORTCOMPLETE $ofile $5) #hybrid analysis
			#ret=$?	
			#if [ $ret -gt 0 ]; then
			#	echo error is "$ret"
			#	echo "$cc"
			#	echo "failure in ANALYTICS hanly subprocess"
			#fi
        fi   
    fi
    if [ "$STATPST" == "true" ]; then # STATPST SRG
		if [ "$ANALYTICS" == "false" ]; then # process the hybrid anlys
			# Hybrid analysis
			if [ "$backend" == "default" ]; then
				# default mode
				if [ -s $logpst ]; then # skip first pass
					if decrypt $xdata2 $logpst; then 			
						awk 'NF' $xdata2 > $ofile # Remove spaces and built the previous search history
						 if [ -s $ofile ]; then 
							sort -u -o $ofile $ofile 
							cc=$(hanly $SORTCOMPLETE $ofile $5) #hybrid analysis		New to version 3
							#ret=$?
							#if [ $ret -ne 0 ]; then
							#	echo "failure in STATPST hanyl subprocess"
							#fi
						fi
						pstc="true"						
					else
						echo "Failed to decrypt log file in hanly for STATPST. log file ${logpst}"
					fi
				else
					pstc="true"
				fi
			else
				if [ -s "$pydbpst" ]; then if ! decrypt "$pydb" "$pydbpst"; then dbc="false" ; else dbc="true"; fi ; fi
				[[ ! -s "$pydbpst" ]] && echo Initializing database... && python3 /usr/local/save-changesnew/pstsrg.py --init && dbc="true"
				if [ -s "$pydbpst" ] && [ "$dbc" == "true" ]; then # Skip first pass
					rt="$(python3 /usr/local/save-changesnew/hanlydb.py $SORTCOMPLETE $COMPLETE $pydb $rout $tfile $checkSUM $cdiag)" # Add Nosuchfile we cant ensure no duplicates just add to the count for marking the file
					ret=$?
					if [ $ret -ne 0 ]; then
						echo "ha failed from hanlydb.py."
					else
						if [ "$rt" == "csm" ]; then
							awk '{ print "\033[31m *** Checksum of file \033[0m" $0 "\033[31m altered without a modified time\033[0m" }' /tmp/cerr && rm /tmp/cerr
						elif [ "$rt" != "" ]; then # Custom feedback
							echo "$rt"
						fi
					fi
					processha # db difffile output	
					[ "$ANALYTICSECT" == "true" ] && [ "$mMODE" == "mc" ] && [ "$rt" != "csm" ] && [ "$dbc" == "true" ] && echo Detected $(nproc 2>/dev/null || echo 1) CPU cores.
				fi		
			fi
		fi
		[[ -n "$cc" && "$cc" == "csum" ]] && { awk '{ print "\033[31m *** Checksum of file \033[0m" $0 "\033[31m altered without a modified time\033[0m" }' /tmp/cerr && rm /tmp/cerr; } || [[ -n "$cc" ]] && echo "Detected $cc CPU cores." #red "*** Checksum of file altered without a modified time."
        if [ -s $rout ]; then # Encrypt stage
            sort -u -o $rout $rout # remove anything already in written
			sed -i -E 's/^([^ ]+) ([^ ]+ [^ ]+) (.+)$/\1,"\2",\3/' $rout
			if [ -s $COMPLETE ]; then cat $COMPLETE >> $rout; fi   # Nosuchfile  cant ensure no duplicates but this action is unique
			if [ "$backend" != "default" ] && [ "$dbc" == "true" ]; then # db mode	if we failed to decompress we dont want to overwrite it
				imsg="$(python3 /usr/local/save-changesnew/pstsrg.py $rout "stats")"
				ret=$?
			elif [ "$backend" == "default" ] && [ "$pstc" == "true" ]; then 
			    imsg="$(storeenc $rout $statpst)" # save and encrypt statpst log  
			    ret=$?
			fi
			if [ $ret -ne 0 ]; then
		        echo "$imsg"
		    else
		        if [ "$imsg" != "" ]; then green "Persistent stats file created."; imsg=""; fi
		    fi
        fi
		# Logfile save
		if [[ "$backend" != "default" && "$dbc" == "true" ]]; then # We do not want to compromise the db if failed to decrypt
			imsg="$(python3 /usr/local/save-changesnew/pstsrg.py $SORTCOMPLETE "log")"
			ret=$?
		elif [ "$backend" == "default" ] && [ "$pstc" == "true" ]; then
		    imsg="$(storeenc $SORTCOMPLETE $logpst "dcr")" # save and encrypt main log
		    ret=$?
		fi
		if [ $ret -ne 0 ]; then
		    echo "$imsg"
		else
		    if [ "$imsg" -ge 0 ] 2>/dev/null; then 
		        if (( imsg % 10 == 0 )); then  cyan "$imsg searches in gpg log"; fi # only output every 10 incriments
		    elif [ "$imsg" != "" ]; then
		        green "Persistent search log file created." # only... creation
		    fi
		fi
		if [ "$backend" != "default" ] && [ "$dbc" == "true" ]; then
			if [ -s "$pydb" ]; then			
				if ! gpg --yes -e -r $email -o $pydbpst $pydb >/dev/null 2>&1; then echo "Failed to encrypt database. Run   gpg --yes -e -r $email -o $pydbpst $pydb  before running again."; else rm "/usr/local/save-changesnew/recent.db"; fi	 
			fi 		
		elif [ "$backend" != "default" ] && [ "$dbc" == "false" ]; then 
			echo Find out why db not decrypting or delete it to make a new one
		fi
		[[ -s "$difffile" ]] && [[ -n "$( tail -n 1 "$difffile")" ]] && [[ "$dbc" == "true" || "$pstc" == "true" ]] && green "Hybrid analysis on"
    fi # End STATPST
	# Loose ends        # Yes if a file changed during search system or cache item.  cdiag detect stealth changes.
	[[ "$cc" != "csum" && -s $slog && "$cdiag" != "true" ]] && cat $slog
	[[ "$cc" != "csum" && -s $slog && "$cdiag" == "true" ]] && { echo; echo "cdiag"; echo ; cat $slog; } >> "$difffile"
	test -f $slog && rm $slog #blank?
    test -f $rout && rm $rout # incase pst off
    filterhits $RECENT $flth # store stats     pass a clean complete list so regex doesnt break
    postop $logf $6 # run post op scripts  ie file doctrine  POSTOP var           IF this is a filtered search or new than file search we do post ops on those specific files
	test -e "$difffile" && chown $USR "$difffile"
fi 
if [ "$ANALYTICS" == "true" ] && [ "$STATPST" == "false" ] ; then 
    stmp $SORTCOMPLETE # save log to /tmp
    if [ ! -f /tmp/rc/full ]; then cyan "Search saved in /tmp"; fi # save in /tmp but make notification go away after full 
fi # Logging complete
#rm -rf $tmp #cleanup
#rm -rf $atmp
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
#test -e /usr/bin/featherpad && featherpad $USRDIR$MODULENAME"${flnm}"
#test -e /usr/bin/xed && xed $USRDIR$MODULENAME"${flnm}"
