#!/bin/bash
#      recentchanges search             Developer Buddy v3.0    08/18/2025
# If some as root calls the program with 2 arguments thats not intended use so exit
# we would fail to get our correct username such as they put a second bogus argument
. /usr/share/porteus/porteus-functions
get_colors
. /usr/local/save-changesnew/comp
. /usr/local/save-changesnew/rntchangesfunctions
if [ `whoami` != "root" ]; then echo "Please enter your root password below" ; su - -c "/usr/local/save-changesnew/recentchangessearch.sh $1 '$2' $3 '$4'" ; exit ; fi
USR=$3
if [ "$USR" == "" ]; then echo please call from recentchanges; exit; fi
if [ "$4" == "" ]; then echo "incorrect usage please call from recentchanges"; exit 1; fi
if [ "$1" != "search" ]; then echo exiting not a search && exit; fi
work=work$$												                    	;		tmp=/tmp/work$$
FLBRAND=`date +"MDY_%m-%d-%y-TIME_%R_%S"|tr ':' '_'`		;		ABSENT=$tmp/absent.txt
BRAND=`date +"MDY_%m-%d-%y-TIME_%R"|tr ':' '_'`				;		chxzm=/rntfiles.xzm
USRDIR=/home/$USR/Downloads											;		RECENT=$tmp/list_recentchanges_filtered.txt
UPDATE=$tmp/save.transferlog.tmp		    							; 		RECENTNUL=$tmp/list_recentchanges_filterednul.txt
COMPLETE=$tmp/list_complete.txt							           		; 		SORTCOMPLETE=$tmp/list_complete_sorted.txt
COMPLETENUL=$tmp/list_completenul.txt							    ;		atmp=/tmp/atmp$$
TMPCOMPLETE=$tmp/tmp_complete.txt									;		tout=$atmp/toutput.tmp
TMPOUTPUT=$tmp/list_tmp_sorted.txt						       		; 		toutnul=$atmp/toutputnul.tmp
flth=/usr/local/save-changesnew/flth.csv						       		;      	xdata=$atmp/logs_stat.log
slog=/tmp/scr																		;     	xdata2=$atmp/logs_log.log
TMPOPT=$tmp/tmp_holding													;		pytmp=$atmp/pytmp.tmp
rout=$atmp/routput.tmp
diffrlt="false"											                        	;		nodiff="false"
validrlt="false"										                           		;		flsrh="false"
pstc="false"
mkdir $tmp
mkdir $atmp
if [ "$ANALYTICSECT" == "true" ]; then start=$(date +%s.%N); fi
if [ "$STATPST" == "true" ]; then
    if [ -f $logpst ]; then
        sz=$( stat -c %s "$logpst")
        if (( ( sz / 1048576 ) > logSIZE )); then
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
		elif (( ( sz / 1048576 )  >= compLVL )); then
	    	nc="true"
        elif (( sz == 0 )); then
            cyan "$logpst is 0 bytes. to resume persistent logging delete file"
            STATPST="false"
        fi
    fi
fi
if [ "$2" != "noarguser" ] && [ "$2" != "" ]; then
	if [ "$2" -ge 0 ] 2>/dev/null; then
        argone=$2
        comp $argone
        tmn=$qtn
		cyan "searching for files $2 seconds old or newer"
    else
        argone=".txt"
    	test -d "${4}" || { echo "Invalid argument ${4} . PWD required."; exit 1; }
		cd "${4}"  || exit
    	filename="$2"
    	test -f "${filename}" || { test -d "${filename}" || echo no such directory file or integer; exit 1; }
    	parseflnm="${2##*/}"
		if [ "$parseflnm" == "" ]; then
    		parseflnm="$(echo "$2" | sed -e 's/\/$//' -e 's@.*/@@')"
    	fi
    	cyan "searching for files newer than $filename "
    	flsrh="true"
    	FEEDFILE=$RECENTNUL
		fc="find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var -newer \"$filename\" -not -type d -print0 "
		ct=$(date +%s)
		fmt=$(stat -c %Y "$filename")
		ag=$(( ct - fmt ))
		fca="find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var \( -cmin -${ag} -o -amin -${ag} \) -not -type d -print0 "
        eval "$fc" 2> /dev/null | tee $RECENTNUL > /dev/null 2> /dev/null
		eval "$fca" 2> /dev/null | tee $toutnul > /dev/null 2> /dev/null
    fi
else
	argone="5" ; tmn=$argone ; cyan "searching for files 5 minutes old or newer"
fi
if [ "$tmn" != "" ]; then
	logf=$RECENT
    FEEDFILE=$COMPLETENUL
	fc="find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var -mmin -${tmn} -not -type d -print0 "
	fca="find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var \( -cmin -${tmn} -o -amin -${tmn} \) -not -type d -print0 "
    eval "$fc" 2> /dev/null | tee $COMPLETENUL > /dev/null 2> /dev/null
	eval "$fca" 2> /dev/null | tee $toutnul > /dev/null 2> /dev/null
fi
if [ "$checkSUM" == "true" ]; then cyan "Running checksum."; fi
if [ "$ANALYTICSECT" == "true" ]; then
	end=$(date +%s.%N)
	if [ "$checkSUM" == "true" ]; then
		  cstart=$(date +%s.%N)
	fi
fi
>$tout
while IFS= read -r -d '' f; do f="${f//$'\n'/\\n}" ; echo "$f" ; done < $FEEDFILE >> $xdata
while IFS= read -r -d '' f; do f="${f//$'\n'/\\n}" ; echo "$f" ; done < $toutnul >> $tout
if [ "$FEEDBACK" == "true" ]; then cat $tout; cat $xdata; fi
if [ -s $tout ]; then grep -Fxv -f $xdata $tout > $TMPCOMPLETE; >$tout; fi
if [ -s $TMPCOMPLETE ]; then
	while IFS= read -r x; do x="${x//$'\\n'/\n}" ; printf '%s\0' "$x"; done < $TMPCOMPLETE > $xdata
	if [ "$mMODE" == "normal" ]; then
		xargs -0 /usr/local/save-changesnew/searchfiles $atmp $tout $COMPLETE $checkSUM < $xdata
	elif [ "$mMODE" == "mem" ]; then
		declare -a xfile
		declare -a ffile
		declare -a nsf
		searcharr $xdata "ctime"
	elif [ "$mMODE" == "mc" ]; then
		xargs -0 -n8 -P4 /usr/local/save-changesnew/searchfiles "$atmp" "$checkSUM" < $xdata
		if compgen -G "$atmp/searchfiles1_*_tmp.log" > /dev/null; then cat "$atmp"/searchfiles1_*_tmp.log > $tout; fi
		if compgen -G "$atmp/searchfiles2_*_tmp.log" > /dev/null; then cat "$atmp"/searchfiles2_*_tmp.log > $COMPLETE; fi
	else
		echo incorrect mMODE && exit
	fi
fi
rm $xdata
if [ "$mMODE" == "normal" ]; then
	xargs -0 /usr/local/save-changesnew/mainloop $atmp $SORTCOMPLETE $COMPLETE $checkSUM < $FEEDFILE
elif [ "$mMODE" == "mem" ]; then
	searcharr $FEEDFILE
	printf "%s\n" "${ffile[@]}" >> $SORTCOMPLETE
	if [ ${#nsf[@]} -gt 0 ]; then printf "%s\n" "${nsf[@]}" > $COMPLETE; fi
elif [ "$mMODE" == "mc" ]; then
	x=$(tr -cd '\0' < $FEEDFILE | wc -c) ; y=8
	if (( x > 100 )); then y=16 ; fi
	xargs -0 -n"$y" -P4 /usr/local/save-changesnew/mainloop "$atmp" "$checkSUM" < $FEEDFILE
	if compgen -G "$atmp/mainloop1_*_tmp.log" > /dev/null; then cat "$atmp"/mainloop1_*_tmp.log > $SORTCOMPLETE;  fi
	if compgen -G "$atmp/mainloop2_*_tmp.log" > /dev/null; then cat "$atmp"/mainloop2_*_tmp.log >> $COMPLETE; fi
fi
if [ "$ANALYTICSECT" == "true" ]; then cend=$(date +%s.%N); fi
if [ -s $SORTCOMPLETE ]; then
	sort -u -o  $SORTCOMPLETE $SORTCOMPLETE
	SRTTIME=$( head -n1 $SORTCOMPLETE | awk '{print $1 " " $2}')
	PRD=$SRTTIME
	if [ ${#xfile[@]} -gt 0 ]; then printf "%s\n" "${xfile[@]}" >> $SORTCOMPLETE; fi
	if [ -s $tout ]; then grep -v 'NOTA-FI-LE 77:77:77' "$tout" | awk -v tme="$PRD" '{ ts = $1 " " $2; if (ts >= tme) print }' > $TMPOPT ; cat $TMPOPT >> $SORTCOMPLETE ; fi
	if [ "$flsrh" != "true" ]; then
		s=$(date -d "$SRTTIME" "+%s")
		if [ "$2" == "noarguser" ]; then
			RANGE=$(( s + 300 ))
		else
			RANGE=$(( s + argone ))
		fi
		PRD=$(date -d "@$RANGE" +'%Y-%m-%d %H:%M:%S')
		grep -v 'NOTA-FI-LE 77:77:77' "$SORTCOMPLETE" | awk -v tme="$PRD" '{ ts = $1 " " $2; if (ts <= tme) print }' > $tout ; mv $tout $SORTCOMPLETE
	fi
	cp $SORTCOMPLETE /home/guest/Ariz
	if [ "$flsrh" == "true" ]; then grep -v 'NOTA-FI-LE 77:77:77' "$SORTCOMPLETE" > $tout ; mv $tout $SORTCOMPLETE ; fi
	sort -u -o  $SORTCOMPLETE $SORTCOMPLETE
	awk '{print $1, $2}' $SORTCOMPLETE > $tout
	perl -nE 'say $1 if /"((?:[^"\\]|\\.)*)"/' "$SORTCOMPLETE" > "$TMPCOMPLETE"
	paste -d' ' $tout $TMPCOMPLETE > $TMPOPT
	sort -o $TMPOPT $TMPOPT
	cat $TMPOPT | grep ' /tmp/' > $TMPOUTPUT
	sort -o $TMPOUTPUT $TMPOUTPUT
	sed -i '/\"\/tmp/d' $SORTCOMPLETE
	sed -i '/ \/tmp/d' $TMPOPT
	cp $TMPOPT $RECENT
fi
if [ "$5" == "filtered" ] || [ "$flsrh" == "true" ]; then
	logf="$TMPOPT"
	if [ "$5" == "filtered" ] && [ "$flsrh" == "true" ]; then logf=$RECENT ; fi
    /usr/local/save-changesnew/filter $TMPOPT $USR
fi
MODULENAME=${chxzm:0:9}
cd $USRDIR
if [ -s $SORTCOMPLETE ] ; then
	validrlt="true"
    if [ "$flsrh" == "true" ]; then
	    flnm="xNewerThan_${parseflnm}"$argone
	    flnmdff="xDiffFromLast_${parseflnm}"$argone
		clearlogs
	    test -e $USRDIR$MODULENAME"${flnm}" && { cp $USRDIR$MODULENAME"${flnm}" $tmp; }
    elif [ "$5" == "filtered" ]; then
	    flnm="xFltchanges_"$argone
	    flnmdff="xFltDiffFromLastSearch_"$argone
        test -e "$USRDIR$MODULENAME$flnm" && cp "$USRDIR$MODULENAME$flnm" $tmp
		[[ ! -s "$tmp$MODULENAME$flnm" ]] && test -e "/tmp/${MODULENAME}${flnm}" && cp "$/tmp${MODULENAME}${flnm}" $tmp
        clearlogs
        if [ -s $TMPOUTPUT ]; then
            cp $TMPOUTPUT $USRDIR$MODULENAME"xFltTmpfiles"$argone
            chown $USR $USRDIR$MODULENAME"xFltTmpfiles"$argone
        fi
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
    test -e $tmp$MODULENAME"${flnm}" && { OLDSORTED=$tmp$MODULENAME"${flnm}" ; comm -23 "${OLDSORTED}" $logf; } > "${difffile}" && nodiff="true"
    cp $logf $USRDIR$MODULENAME"${flnm}"
    chown $USR $USRDIR$MODULENAME"${flnm}"
    if [ -s "${difffile}" ]; then
    	diffrlt="true"
    	CDATE=$( head -n1 $SORTCOMPLETE | awk '{print $1 " " $2}')
        if [ "$flsrh" == "false" ]; then awk -v tme="$CDATE" '$0 >= tme' "$difffile" > $TMPCOMPLETE ; else cat "${difffile}" > $TMPCOMPLETE; fi
    	echo >> "${difffile}"
    	while IFS="" read -r p || [ -n "$p" ]; do cFILE="$( echo "$p" | cut -d " " -f3-)" ; cFILE="$( escapef "$cFILE")" ; grep -Fqs "$cFILE" $SORTCOMPLETE && { echo "Modified" "$p" >> $ABSENT; echo "Modified" "$p" >> $rout; } || { echo "Deleted " "$p" >> $ABSENT; echo "Deleted" "$p" >> $rout; } ; done < $TMPCOMPLETE
		test -f $ABSENT  && { echo Applicable to your search ; cat $ABSENT ; } >> "${difffile}" || { echo "None of above is applicable to search. It is the previous search"; } >> "${difffile}"
    else
        test -e "${difffile}" && rm "${difffile}"
    fi

	ofile=$atmp/tmpinfo ; tfile=$atmp/tmpd
    if [ -d /tmp/rc ] && [ "$ANALYTICS" == "true" ] && [ "$STATPST" == "false" ]; then
        for file in /tmp/rc/*; do
            cat $file >> $ofile  2> /dev/null
        done
        if [ -s $ofile ]; then
            sort -u -o $ofile $ofile
			hanly $SORTCOMPLETE $ofile $5
			ret=$?
			if [ "$ret" -gt 0 ]; then
				echo "failure in ANALYTICS hanly subprocess"
			fi
        fi
    fi

    if [ "$STATPST" == "true" ]; then
		if [ "$ANALYTICS" == "false" ]; then
			if [ "$backend" == "default" ]; then
				if [ -s $logpst ]; then
					if decrypt $xdata2 $logpst; then
						awk 'NF' $xdata2 > $ofile
						 if [ -s $ofile ]; then
							sort -u -o $ofile $ofile
							hanly $SORTCOMPLETE $ofile $5
							ret=$?
							if [ "$ret" -ne 0 ]; then
								echo "failure in STATPST hanyl subprocess"
							fi
						fi
						pstc="true"
					else
						echo "Failed to decrypt log file in hanly for STATPST. log file ${logpst}"
					fi
				else
					pstc="true"
				fi
				if [ "$pstc" == "true" ]; then
					imsg="$(storeenc $SORTCOMPLETE $logpst "dcr")"
					ret=$?
					if [ "$ret" -ne 0 ]; then
						echo "$imsg"
					else
						if [ "$imsg" -ge 0 ] 2>/dev/null; then
							if (( imsg % 10 == 0 )); then  cyan "$imsg searches in gpg log"; fi
						elif [ "$imsg" != "" ]; then
							green "Persistent search log file created."
						fi
					fi
					if [ -s $rout ]; then
						sort -u -o $rout $rout
						sed -i -E 's/^([^ ]+) ([^ ]+ [^ ]+) (.+)$/\1,"\2",\3/' $rout
						if [ -s $COMPLETE ]; then cat $COMPLETE >> $rout; fi
						if [ "$pstc" == "true" ]; then
							imsg="$(storeenc $rout $statpst)"
							ret=$?
							if [ "$ret" -ne 0 ]; then
								echo "$imsg"
							else
								if [ "$imsg" != "" ]; then green "Persistent stats file created."; imsg=""; fi
							fi
						fi
					fi
				fi
			else

				python3 /usr/local/save-changesnew/pstsrg.py $SORTCOMPLETE $pydbpst $rout $tfile $checkSUM $cdiag $email $mMODE $ANALYTICSECT
				ret=$?
				if [ "$ret" -ne 0 ]; then
					if [ "$ret" -eq 2 ] || [ "$ret" -eq 3 ]; then
						echo "Problem with GPG refer to instructions on setting up pinentry ect. Database preserved."
					elif [ "$ret" -eq 4 ]; then
						echo "Problem with database in psysrg.py"
					else
						echo "Pstsrg.py failed. exitcode ${ret}"
					fi
				fi

				processha

			fi
		fi
    fi
	[[ -s "$difffile" ]] && [[ -n "$( tail -n 1 "$difffile")" ]] && [[ "$ANALYTICSECT" == "true" ]] && green "Hybrid analysis on"
	[[ "$cc" != "csum" && -s $slog && "$cdiag" != "true" ]] && cat $slog
	[[ "$cc" != "csum" && -s $slog && "$cdiag" == "true" ]] && { echo; echo "cdiag"; echo ; cat $slog; } >> "$difffile"
	test -f $slog && rm $slog ; test -f $rout && rm $rout
    filterhits $RECENT $flth
    postop $logf $6
	test -e "$difffile" && chown $USR "$difffile"
fi
if [ "$ANALYTICS" == "true" ] && [ "$STATPST" == "false" ] ; then stmp $SORTCOMPLETE && [[ ! -f /tmp/rc/full ]] && cyan "Search saved in /tmp" ; fi
rm -rf $tmp ; rm -rf $atmp
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
if [ "$nodiff" == "true" ] && [ "$diffrlt" == "false" ]; then green "There was no difference file. That is the results themselves are true." ; fi
if [ "$validrlt" == "false" ]; then green  "No new files to report." ; echo; fi
#test -e /usr/bin/featherpad && featherpad $USRDIR$MODULENAME"${flnm}"
#test -e /usr/bin/xed && xed $USRDIR$MODULENAME"${flnm}"
