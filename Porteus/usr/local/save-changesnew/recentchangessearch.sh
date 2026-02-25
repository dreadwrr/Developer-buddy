#!/bin/bash
#      recentchanges search             Developer Buddy v5.0     01/13/2026
. /usr/share/porteus/porteus-functions
get_colors
. /usr/local/save-changesnew/rntchangesfunctions
USR=$3
if [ "$USR" == "" ]; then echo please call from recentchanges; exit; fi
if [ "$4" == "" ]; then echo "incorrect usage please call from recentchanges"; exit 1; fi
if [ "$1" != "search" ]; then echo exiting not a search && exit; fi

convertn() {
local x
    x=$( echo "scale=2; $1 / $2" | bc)
    echo "$x"
}

#VARS
# tmp files
# tfile TMPCOMPLETE TMPOUTPUT
# tout used for ctime loop then available for tmp file ln137
# tfile3 used in backend 
# spare tmp file  tfile2
# spare tmp file xdata3
# xopt aux tmp dir
# $tmp  main search
# $atmp  secondary tmp files from upgrade
# $atmpwork   multiprocessing tmp files from main search so not messy
# $atmp$workdir   restricted decrypted pst file for ha. & ha multiprocessing related files
workfld=/fsearch$$														;		workdir=/hablk
tmp=/tmp/work$$															;		atmp=/tmp/atmp$$
chxzm=/$MODULENAME.xzm											;		rout=$atmp/routput.tmp
UPDATE=$tmp/save.transferlog.tmp								;		tout=$atmp/toutput.tmp
ABSENT=$tmp/absent.txt												;		toutnul=$atmp/toutputnul.tmp
RECENT=$tmp/list_recentchanges_filtered.txt					;		xdata=/logs_stat.log
RECENTNUL=$tmp/list_recentchanges_filterednul.txt		;		xdata2=/logs_log.log
SORTCOMPLETE=$tmp/list_complete_sorted.txt				;		xdata3=$atmp$workdir/temp_log.log
TMPOUTPUT=$tmp/list_tmp_sorted.txt							;		tfile=$atmp$xdata
TMPOPT=$tmp/tmp_holding											;		tfile2=$atmp$xdata2
COMPLETE=$tmp/list_complete.txt									;		pytmp=$atmp/pytmp.tmp
COMPLETENUL=$tmp/list_completenul.txt						;		flth=/usr/local/save-changesnew/flth.csv
TMPCOMPLETE=$tmp/tmp_complete.txt							;		LCLMODULENAME=${chxzm:1:8}
slog=/tmp/scr																;		USRDIR=/home/$USR/Downloads
cerr=/tmp/cerr																;		log_file=/tmp/file_creation_log.txt

cores=0                                                     					;		max_jobs=0
OLDSORTED=""
cached=/tmp/dbctimecache/
CACHE_F="${cached}ctimecache"
BRAND=$(date +"MDY_%m-%d-%y-TIME_%R" | tr ':' '_')
FLBRAND=$(date +"MDY_%m-%d-%y-TIME_%R_%S" | tr ':' '_')
fmt="%Y-%m-%d %H:%M:%S"

diffrlt="false"						; 		nodiff="false"
pstc="false"							;		flsrh="false"
samerlt="false"						;		nc="false"
syschg="false"						;		csm="false"
csum="false"


F=(/bin /etc /home /lib /lib64 /opt /root /sbin /tmp /usr /var)
TAIL=(-not -type d -printf '%T@ %A@ %C@ %i %M %n %s %u %g %m %p\0')

mkdir $tmp
mkdir $atmp
mkdir $atmp$workfld
mkdir $atmp$workdir
intst

if [ "$2" != "noarguser" ] && [ "$2" != "" ]; then # If a desired time is specified we will search for that  (in seconds)
    p=60
	if [ "$2" -ge 0 ] 2>/dev/null; then # is it a number
        argone=$2
        tmn=$( convertn $argone $p)
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
        ag=$( convertn $ag $p)
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


[[ ! -d "$cached" ]] && mkdir $cached && chmod 700 $cached
[[ "$checkSUM" = "true" ]] && [[ "$ANALYTICS" = "true" || "$STATPST" = "true" ]] && cyan "Running checksum." || checkSUM="false"

if [ ! -s "$tout" ]; then
	find "${F[@]}" "${MMIN[@]}" "${TAIL[@]}" 2>/dev/null | tee $FEEDFILE > /dev/null 2>&1
	find "${F[@]}" "${CMIN[@]}" "${TAIL[@]}" 2>/dev/null | tee $toutnul > /dev/null 2>&1
	end=$(date +%s.%N) ; [[ "$checkSUM" == "true" ]] && [[ "$ANALYTICSECT" ]] && cstart=$(date +%s.%N)
	ctimeloop $FEEDFILE $atmp$xdata # dont keep xdata
else
	find "${F[@]}" "${MMIN[@]}" "${TAIL[@]}" 2>/dev/null | tee $FEEDFILE > /dev/null 2>&1
	end=$(date +%s.%N) ; [[ "$checkSUM" == "true" ]] && [[ "$ANALYTICSECT" ]] && cstart=$(date +%s.%N)
fi

if [ "$FEEDBACK" == "true" ]; then #scrolling look
	tr '\0' '\n' < "$FEEDFILE" | awk '{ $1=$2=$3=$4=$5=$6=$7=$8=$9=$10=""; sub(/^ +/, ""); print }'
	#tr '\0' '\n' < "$toutnul" | awk '{ $1=$2=$3=$4=$5=$6=$7=$8=$9=$10=""; sub(/^ +/, ""); print }'  
fi 
#while IFS= read -r -d '' y; do y="$( ap_enc "$y")" ; printf '%s\n' "$y"; done < $FEEDFILE > $xdata

search $FEEDFILE $SORTCOMPLETE $COMPLETE $checkSUM "main" batch1
cend=$(date +%s.%N)
[[ -f "$CACHE_F" ]] && chmod 600 "$CACHE_F"

if [ -s $SORTCOMPLETE ]; then
	syschg="true"

	sort -u -o  $SORTCOMPLETE $SORTCOMPLETE ; SRTTIME=$( head -n1 $SORTCOMPLETE | awk '{print $1 " " $2}') ; PRD=$SRTTIME

	# Insert $tout \ deduplicate
	merge_ctime $SORTCOMPLETE $tout $PRD  #if [ -s $tout ]; then awk -v tme="$PRD" '{ ts = $1 " " $2; if (ts >= tme) print }' $tout >> $SORTCOMPLETE ; fi  # original doesnt dedupe
	inclusions $SORTCOMPLETE

	if [ "$flsrh" != "true" ]; then
		s=$(date -d "$SRTTIME" "+%s")
		if [ "$2" == "noarguser" ]; then RANGE=$(( s + 300 )) ; else RANGE=$(( s + argone )) ; fi
		PRD=$(date -d "@$RANGE" +"$fmt")
		awk -v tme="$PRD" '{ ts = $1 " " $2; if (ts <= tme) print }' $SORTCOMPLETE > $tout ; mv $tout $SORTCOMPLETE
	fi
	sort -u -o $SORTCOMPLETE $SORTCOMPLETE

	process_sort $SORTCOMPLETE $TMPOPT  #decode from log \ search results 
	#	awk '{print $1, $2}' $SORTCOMPLETE > $tout      original
	#	perl -nE 'say $1 if /"((?:[^"\\]|\\.)*)"/' "$SORTCOMPLETE" > "$TMPCOMPLETE"
	#	paste -d' ' $tout $TMPCOMPLETE > $TMPOPT
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

cd $USRDIR || exit
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

    [[ -n "$OLDSORTED" ]] && test -e $OLDSORTED && sort -o $OLDSORTED $OLDSORTED && comm -23 "$OLDSORTED" $logf > "$difffile"

	[[ "$nodiff" = "false" ]] && test -e $tmp$MODULENAME"$flnm" && { OLDSORTED=$tmp$MODULENAME"$flnm" ; sort -o $OLDSORTED $OLDSORTED ; comm -23 "$OLDSORTED" $logf; } > "$difffile" && nodiff="true"
    cp $logf $USRDIR$MODULENAME"$flnm"
    chown $USR $USRDIR$MODULENAME"$flnm"
   

    isdiff "$difffile" $RECENT $TMPCOMPLETE
    
	backend $5
    filterhits $RECENT $flth
    postop $SORTCOMPLETE $6 $5 $flsrh
	test -e "$difffile" && chown $USR "$difffile"
fi

if [ "$ANALYTICS" == "true" ] && [ "$STATPST" == "false" ] ; then stmp $SORTCOMPLETE && [[ ! -f /tmp/rc/full ]] && cyan "Search saved in /tmp" ; fi

test -d "$atmp" && rm -rf "${atmp:?}"
test -d "$tmp" && rm -rf "${tmp:?}"

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
