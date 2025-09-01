#!/bin/bash
#      recentchanges search             Developer Buddy v3.0    08/28/2025
. /usr/share/porteus/porteus-functions
get_colors
. /usr/local/save-changesnew/rntchangesfunctions
if [ `whoami` != "root" ]; then echo "Please enter your root password below" ; su - -c "/usr/local/save-changesnew/recentchangessearch.sh $1 '$2' $3 '$4'" ; exit ; fi
USR=$3
if [ "$USR" == "" ]; then echo please call from recentchanges; exit; fi
if [ "$4" == "" ]; then echo "incorrect usage please call from recentchanges"; exit 1; fi
if [ "$1" != "search" ]; then echo exiting not a search && exit; fi
work=work$$													        ;		atmp=/tmp/atmp$$
tmp=/tmp/work$$												        ;		rout=$atmp/routput.tmp
chxzm=/rntfiles.xzm											        ;		tout=$atmp/toutput.tmp
USRDIR=/home/$USR/Downloads								;		toutnul=$atmp/toutputnul.tmp
slog=/tmp/scr												            ;		xdata=$atmp/logs_stat.log
UPDATE=$tmp/save.transferlog.tmp							;		xdata2=$atmp/logs_log.log
ABSENT=$tmp/absent.txt										    ;		xdata3=$atmp/db_log.log
RECENT=$tmp/list_recentchanges_filtered.txt				;		pytmp=$atmp/pytmp.tmp
RECENTNUL=$tmp/list_recentchanges_filterednul.txt	;		COMPLETE=$tmp/list_complete.txt
SORTCOMPLETE=$tmp/list_complete_sorted.txt			;		COMPLETENUL=$tmp/list_completenul.txt
TMPOUTPUT=$tmp/list_tmp_sorted.txt						;		TMPCOMPLETE=$tmp/tmp_complete.txt
TMPOPT=$tmp/tmp_holding										;		flth=/usr/local/save-changesnew/flth.csv
OLDSORTED=""
diffrlt="false" 											; 		nodiff="false"
validrlt="false"											;		flsrh="false"
pstc="false"
BRAND=$(date +"MDY_%m-%d-%y-TIME_%R" | tr ':' '_')
FLBRAND=$(date +"MDY_%m-%d-%y-TIME_%R_%S" | tr ':' '_')
mkdir $tmp
mkdir $atmp
intst
if [ "$2" != "noarguser" ] && [ "$2" != "" ]; then # If a desired time is specified we will search for that  (in seconds)
	if [ "$2" -ge 0 ] 2>/dev/null; then # is it a number
        argone=$2 #What the user passed
	 	p=60       # divider
	 	# is it a number
    	argone=$2  #What the user passed
        tmn=$( echo "scale=2; $argone /$p" | bc)
		if [ $(( $argone % $p )) -eq 0 ]; then tmn=$(( $argone / $p )); fi
		cyan "searching for files $2 seconds old or newer"
    else
        argone=".txt"
    	test -d "${4}" || { echo "Invalid argument ${4} . PWD required."; exit 1; }
		cd "${4}"  || exit
    	filename="$2"
    	test -f "${filename}" || { test -d "${filename}" || echo no such directory file or integer; exit 1; }
    	parseflnm="${2##*/}"
		if [ "$parseflnm" == "" ]; then parseflnm="$(echo "$2" | sed -e 's/\/$//' -e 's@.*/@@')" ; fi
    	cyan "searching for files newer than $filename "
    	flsrh="true"
    	FEEDFILE=$RECENTNUL
		fc="find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var -newer \"$filename\" -not -type d -print0 "
		ct=$(date +%s)
		fmt=$(stat -c %Y "$filename")
		ag=$(( ct - fmt ))
		fca="find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var \( -cmin -${ag} -o -amin -${ag} \) -not -type d -print0 "
    fi
else
	argone="5" ; tmn=$argone ; cyan "searching for files 5 minutes old or newer"
fi
if [ "$tmn" != "" ]; then
	logf=$RECENT ; FEEDFILE=$COMPLETENUL
	fc="find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var -mmin -${tmn} -not -type d -print0 "
	fca="find /bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var \( -cmin -${tmn} -o -amin -${tmn} \) -not -type d -print0 "
fi
eval "$fc" 2> /dev/null | tee $FEEDFILE > /dev/null 2> /dev/null
eval "$fca" 2> /dev/null | tee $toutnul > /dev/null 2> /dev/null
ctimeloop $FEEDFILE $xdata
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
	sort -u -o  $SORTCOMPLETE $SORTCOMPLETE ; SRTTIME=$( head -n1 $SORTCOMPLETE | awk '{print $1 " " $2}') ; PRD=$SRTTIME
	if [ ${#xfile[@]} -gt 0 ]; then printf "%s\n" "${xfile[@]}" >> $SORTCOMPLETE; fi
	if [ -s $tout ]; then grep -v 'NOTA-FI-LE 77:77:77' "$tout" | awk -v tme="$PRD" '{ ts = $1 " " $2; if (ts >= tme) print }' > $TMPOPT ; cat $TMPOPT >> $SORTCOMPLETE ; fi
	if [ "$flsrh" != "true" ]; then
		s=$(date -d "$SRTTIME" "+%s")
		if [ "$2" == "noarguser" ]; then RANGE=$(( s + 300 )) ; else RANGE=$(( s + argone )) ; fi
		PRD=$(date -d "@$RANGE" +'%Y-%m-%d %H:%M:%S')
		grep -v 'NOTA-FI-LE 77:77:77' "$SORTCOMPLETE" | awk -v tme="$PRD" '{ ts = $1 " " $2; if (ts <= tme) print }' > $tout ; mv $tout $SORTCOMPLETE
	else
		grep -v 'NOTA-FI-LE 77:77:77' "$SORTCOMPLETE" > $tout ; mv $tout $SORTCOMPLETE
	fi
	sort -u -o  $SORTCOMPLETE $SORTCOMPLETE
	if [ "$updatehlinks" == "true" ] && [ "$backend" == "database" ]; then ulink $SORTCOMPLETE $tout; fi
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
MODULENAME=${chxzm:0:9} ; LCLMODULENAME=${chxzm:1:8} ; cd $USRDIR
if [ -s $SORTCOMPLETE ] ; then
	validrlt="true"
    if [ "$flsrh" == "true" ]; then
	    flnm="xNewerThan_${parseflnm}"$argone
	    flnmdff="xDiffFromLast_${parseflnm}"$argone
	    test -e $USRDIR$MODULENAME"${flnm}" && cp $USRDIR$MODULENAME"${flnm}" $tmp
    elif [ "$5" == "filtered" ]; then
	    flnm="xFltchanges_"$argone
	    flnmdff="xFltDiffFromLastSearch_"$argone
        test -e "$USRDIR$MODULENAME$flnm" && cp "$USRDIR$MODULENAME$flnm" $tmp
    else
	    flnm="xSystemchanges"$argone
	    flnmdff="xSystemDiffFromLastSearch"$argone
	    test -e $USRDIR$MODULENAME$flnm && cp $USRDIR$MODULENAME$flnm $tmp
		[[ ! -s "$tmp$MODULENAME$flnm" ]] && test -e "/tmp/${MODULENAME}${flnm}" && cp "/tmp${MODULENAME}${flnm}" $tmp
		[[ ! -s "$tmp$MODULENAME$flnm" ]] && cd /tmp && { hsearch ; cd $USRDIR; }
    fi
	clearlogs
    if [ -s $TMPOUTPUT ]; then
		cp $TMPOUTPUT $USRDIR$MODULENAME"xSystemTmpfiles${parseflnm}${argone%.txt}"
		chown $USR $USRDIR$MODULENAME"xSystemTmpfiles${parseflnm}${argone%.txt}"
	fi
    difffile=$USRDIR$MODULENAME"${flnmdff}"
    [[ -n "$OLDSORTED" ]] && test -e $OLDSORTED && comm -23 "$OLDSORTED" $logf > "${difffile}"
	[[ "$nodiff" == "false" ]] && test -e $tmp$MODULENAME"${flnm}" && { OLDSORTED=$tmp$MODULENAME"${flnm}" ; comm -23 "${OLDSORTED}" $logf; } > "${difffile}" && nodiff="true"
    cp $logf $USRDIR$MODULENAME"${flnm}"
    chown $USR $USRDIR$MODULENAME"${flnm}"
    if [ -s "${difffile}" ]; then
    	diffrlt="true"
    	CDATE=$( head -n1 $SORTCOMPLETE | awk '{print $1 " " $2}')
        if [ "$flsrh" == "false" ]; then awk -v tme="$CDATE" '$0 >= tme' "$difffile" > $TMPCOMPLETE ; else cat "${difffile}" > $TMPCOMPLETE; fi
    	echo >> "${difffile}"
    	while IFS="" read -r p || [ -n "$p" ]; do cFILE="$( echo "$p" | cut -d " " -f3-)" ; grep -Fqs "$cFILE" $SORTCOMPLETE && { echo "Modified" "$p" >> $ABSENT; echo "Modified" "$p" >> $rout; } || { echo "Deleted " "$p" >> $ABSENT; echo "Deleted" "$p" >> $rout; } ; done < $TMPCOMPLETE
		test -f $ABSENT  && { echo Applicable to your search ; cat $ABSENT ; } >> "${difffile}" || { echo "None of above is applicable to search. It is the previous search"; } >> "${difffile}"
    else
        test -e "${difffile}" && rm "${difffile}"
    fi
	backend
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
#if [ -z "$AGENT_PID" ]; then kill "$AGENT_PID"; fi
