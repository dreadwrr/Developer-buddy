#!/bin/bash
#      recentchanges search             Developer Buddy v3.0     9/19/2025
. /usr/share/porteus/porteus-functions
get_colors
. /usr/local/save-changesnew/rntchangesfunctions
USR=$3
if [ "$USR" == "" ]; then echo please call from recentchanges; exit; fi
if [ "$4" == "" ]; then echo "incorrect usage please call from recentchanges"; exit 1; fi
if [ "$1" != "search" ]; then echo exiting not a search && exit; fi

work=work$$															;   atmp=/tmp/atmp$$
tmp=/tmp/work$$														;   rout=$atmp/routput.tmp
chxzm=/rntfiles.xzm													;   tout=$atmp/toutput.tmp
USRDIR=/home/$USR/Downloads								;   toutnul=$atmp/toutputnul.tmp
slog=/tmp/scr															;   xdata=/logs_stat.log
UPDATE=$tmp/save.transferlog.tmp							;   xdata2=/logs_log.log
ABSENT=$tmp/absent.txt											;   xdata3=/db_log.log
RECENT=$tmp/list_recentchanges_filtered.txt				;   pytmp=$atmp/pytmp.tmp
RECENTNUL=$tmp/list_recentchanges_filterednul.txt	;   COMPLETE=$tmp/list_complete.txt
SORTCOMPLETE=$tmp/list_complete_sorted.txt			;   COMPLETENUL=$tmp/list_completenul.txt
TMPOUTPUT=$tmp/list_tmp_sorted.txt						;   TMPCOMPLETE=$tmp/tmp_complete.txt
TMPOPT=$tmp/tmp_holding										;   flth=/usr/local/save-changesnew/flth.csv
log_file=/tmp/file_creation_log.txt								;	cerr=/tmp/cerr

OLDSORTED=""
csm=""
																
cores=0																	;   max_jobs=0

OLDSORTED=""
CACHE_F=/tmp/ctimecache
fmt="%Y-%m-%d %H:%M:%S"                                     
BRAND=$(date +"MDY_%m-%d-%y-TIME_%R" | tr ':' '_')     
FLBRAND=$(date +"MDY_%m-%d-%y-TIME_%R_%S" | tr ':' '_')

diffrlt="false"															; 		nodiff="false"
pstc="false"																;		flsrh="false"
samerlt="false"															;		nc="false"
syschg="false"


F=(/bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var)
TAIL=(-not -type d -printf '%T@ %A@ %C@ %i %s %u %g %m %p\0')

intst
mkdir $tmp
mkdir $atmp

if [ "$2" != "noarguser" ] && [ "$2" != "" ]; then # If a desired time is specified we will search for that  (in seconds)
	if [ "$2" -ge 0 ] 2>/dev/null; then # is it a number
        argone=$2
	 	p=60
        tmn=$( echo "scale=2; $argone /$p" | bc)
		if [ $(( $argone % $p )) -eq 0 ]; then tmn=$(( $argone / $p )); fi
		cyan "searching for files $2 seconds old or newer"
    else
        argone=".txt"
    	test -d "$4" || { echo "Invalid argument ${4} . PWD required."; exit 1; }
		cd "$4"  || exit
    	filename="$2"
    	test -f "$filename" || { test -d "$filename" || echo no such directory file or integer; exit 1; }
    	parseflnm="${2##*/}"
		if [ "$parseflnm" == "" ]; then parseflnm="$(echo "$2" | sed -e 's/\/$//' -e 's@.*/@@')" ; fi
    	cyan "searching for files newer than $filename "
    	flsrh="true"
    	FEEDFILE=$RECENTNUL
		ct=$(date +%s)
		fmt=$(stat -c %Y "$filename")
		ag=$(( ct - fmt ))
		MMIN=(-newer "$filename")
		CMIN=(-cmin "-${ag}")
    fi
else
	argone="5" ; tmn=$argone ; cyan "searching for files 5 minutes old or newer"
fi
if [ "$tmn" != "" ]; then
	logf=$RECENT ; FEEDFILE=$COMPLETENUL
	MMIN=(-mmin "-${tmn}")
	CMIN=(-cmin "-${tmn}")
fi

[[ "$checkSUM" = "true" ]] && [[ "$ANALYTICS" = "true" || "$STATPST" = "true" ]] && cyan "Running checksum." || checkSUM="false"
if [ -z "$tout" ]; then
	find "${F[@]}" "${MMIN[@]}" "${TAIL[@]}" 2>/dev/null | tee $FEEDFILE > /dev/null 2>&1
	find "${F[@]}" "${CMIN[@]}" "${TAIL[@]}" 2>/dev/null | tee $toutnul > /dev/null 2>&1
	if [[ "$ANALYTICSECT" = "true" ]]; then end=$(date +%s.%N) ; [[ "$checkSUM" == "true" ]] && cstart=$(date +%s.%N) ; fi	
	ctimeloop $FEEDFILE $atmp$xdata # dont keep xdata
else
	find "${F[@]}" "${MMIN[@]}" "${TAIL[@]}" 2>/dev/null | tee $FEEDFILE > /dev/null 2>&1
	if [[ "$ANALYTICSECT" = "true" ]]; then end=$(date +%s.%N) ; [[ "$checkSUM" == "true" ]] && cstart=$(date +%s.%N) ; fi	
fi

if [ "$FEEDBACK" == "true" ]; then #scrolling look
	tr '\0' '\n' < "$FEEDFILE" | awk '{ $1=$2=$3=$4=$5=$6=$7=$8=""; sub(/^ +/, ""); print }'
	#tr '\0' '\n' < "$toutnul" | awk '{ $1=$2=$3=$4=$5=$6=$7=$8=""; sub(/^ +/, ""); print }'  
fi 

#while IFS= read -r -d '' y; do y="$( escf "$y")" ; printf '%s\n' "$y"; done < $FEEDFILE > $xdata
search $FEEDFILE $SORTCOMPLETE $COMPLETE $checkSUM "main"
isoutput mainloop1* mainloop2* $SORTCOMPLETE $COMPLETE
isoutput cache1* $CACHE_F

LCLMODULENAME=${chxzm:1:8}

if [ "$ANALYTICSECT" == "true" ]; then cend=$(date +%s.%N); fi
if [ -s $SORTCOMPLETE ]; then
	syschg="true"
	
	sort -u -o  $SORTCOMPLETE $SORTCOMPLETE ; SRTTIME=$( head -n1 $SORTCOMPLETE | awk '{print $1 " " $2}') ; PRD=$SRTTIME
	if [ -s $tout ]; then awk -v tme="$PRD" '{ ts = $1 " " $2; if (ts >= tme) print }' $tout >> $SORTCOMPLETE ; fi

	inclusions

	if [ "$flsrh" != "true" ]; then
		s=$(date -d "$SRTTIME" "+%s")
		if [ "$2" == "noarguser" ]; then RANGE=$(( s + 300 )) ; else RANGE=$(( s + argone )) ; fi
		PRD=$(date -d "@$RANGE" +"$fmt")
		awk -v tme="$PRD" '{ ts = $1 " " $2; if (ts <= tme) print }' $SORTCOMPLETE > $tout ; mv $tout $SORTCOMPLETE
	fi

	sort -u -o $SORTCOMPLETE $SORTCOMPLETE
	if [[ "$updatehlinks" = "true" && "$backend" = "database" && "$STATPST" = "true" ]]; then ulink $SORTCOMPLETE $tout; fi
	awk '{print $1, $2}' $SORTCOMPLETE > $tout
	perl -nE 'say $1 if /"((?:[^"\\]|\\.)*)"/' "$SORTCOMPLETE" > "$TMPCOMPLETE"
	paste -d' ' $tout $TMPCOMPLETE > $TMPOPT
	cat $TMPOPT | grep ' /tmp/' > $TMPOUTPUT
	sort -o $TMPOUTPUT $TMPOUTPUT
	sed -i '/\"\/tmp/d' $SORTCOMPLETE
	sed -i '/ \/tmp/d' $TMPOPT
	sort -o $TMPOPT $TMPOPT
	cp $TMPOPT $RECENT
fi

if [ "$5" == "filtered" ] || [ "$flsrh" == "true" ]; then
	logf="$TMPOPT"
	if [ "$5" == "filtered" ] && [ "$flsrh" == "true" ]; then logf=$RECENT ; fi 
    /usr/local/save-changesnew/filter $TMPOPT $USR
fi

cd $USRDIR
MODULENAME=${chxzm:0:9}


if [ -s $SORTCOMPLETE ] ; then
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

    [[ -n "$OLDSORTED" ]] && test -e $OLDSORTED && comm -23 "$OLDSORTED" $logf > "$difffile"
	[[ "$nodiff" = "false" ]] && test -e $tmp$MODULENAME"$flnm" && { OLDSORTED=$tmp$MODULENAME"$flnm" ; comm -23 "$OLDSORTED" $logf; } > "$difffile" && nodiff="true"
    cp $logf $USRDIR$MODULENAME"$flnm"
    chown $USR $USRDIR$MODULENAME"$flnm"
    isdiff "$difffile" $TMPCOMPLETE
	backend $5
    filterhits $RECENT $flth
    postop $logf $6
	test -e "$difffile" && chown $USR "$difffile"
fi

if [ "$ANALYTICS" = "true" ] && [ "$STATPST" = "false" ] ; then stmp $SORTCOMPLETE && [[ ! -f /tmp/rc/full ]] && cyan "Search saved in /tmp" ; fi
rm -rf $tmp
rm -rf $atmp
if [ "$ANALYTICSECT" = "true" ]; then
    el=$(awk "BEGIN {print $end - $start}")
    printf "Search took %.3f seconds.\n" "$el"
	if [ "$checkSUM" = "true" ]; then
		el=$(awk "BEGIN {print $cend - $cstart}")
		printf "Checksum took %.3f seconds.\n" "$el"
	fi
fi
if [ "$flsrh" = "true" ]; then
    cyan "All files newer than ""${filename}""  in /Downloads"
    echo
elif [ "$5" = "filtered" ]; then
    cyan "All new filtered files are listed in /Downloads"
else
  	cyan "All new system files are listed  in /Downloads"
  	echo
fi
logic
display $USRDIR $MODULENAME"$flnm"
#if [ -n "$AGENT_PID" ]; then kill "$AGENT_PID"; fi
