#!/usr/bin/env bash
#     recentchanges general functions    validprogram       gettime                                                                07/4/2025
#This function returns the root directory or null if it is in  /  of system
validprogram() {
local LOGFILE=$1	; local FCOUNT=0
local BASEDIR=""	; local DEPTH=0
local y=0				; local p=0
local z=""				; local strt=0
local ABSTRING=""
local BCSTRING=""
local CDSTRING=""
BASEDIR=$( cat $LOGFILE | uniq -c | sort -sr | head -n 1 | awk '{print $2}')
DEPTH=$( echo "${BASEDIR}" | awk -F '/' '{print NF-1}')
FCOUNT=$( grep -c "${BASEDIR}" $LOGFILE)
p=0
z=$( insetdirectory)
if [ "$z" != "" ]; then
	if (( z = DEPTH)); then
    	strt=$z
    else
    	strt=$(( z + 1))
    fi
else
    strt=2
fi
for ((i=strt; i<=DEPTH; i++))
do
	IDIR=$( echo "${BASEDIR}" | cut -d '/' -f 1-$i)
	y=$( grep -c "^${IDIR}" $LOGFILE)
	if (( y >= p )); then
		p=$y
		CDSTRING=$IDIR
	else
		break
	fi
done
BASEDIR=$CDSTRING
echo "${BASEDIR}"
}
#iis system directory and return the root directory
insetdirectory() {
local result
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
template+=("/root/")
template+=("/sbin/")
template+=("/usr/bin/")
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
    if [ "$result" != "" ]; then
        d=$( echo "${result}" | awk -F '/' '{print NF-1}')
        echo $d
	    break
    else
        echo ""
    fi
done
}
gettime() {
local SRTTIME	;	local FINTIME
local s				;	local f
local ENDTM		;	local RANGE
local PRD			;	local ST
local FN
SRTTIME=$( head -n1 $SORTCOMPLETE | awk '{print $1 " " $2}')
s=$(date -d "$SRTTIME" "+%s")
RANGE=$(( s + argone ))
if [ "$THETIME" == "noarguser" ]; then
	RANGE=$(( s + 300 ))
fi
PRD=$(date -d "@$RANGE" +'%Y-%m-%d %H:%M:%S')
FINTIME=$( awk -F" " -v tme="$PRD" '$0 < tme' $SORTCOMPLETE | sort -sr | head -n 1 | awk -F ' ' '{print $1 " " $2}')
f=$(date -d "$FINTIME" "+%s")
DIFFTIME=$(( f - s ))
ENDTM=$(date -d "@$DIFFTIME" -u +'%H:%M:%S')
FN=$( tail -n1 $1 | awk '{print $2}') ; f=$(date -d "$FN" "+%s")
ST=$( head -n1 $1 | awk '{print $2}') ; sSRC=$( date -d "$ST" "+%s")
eSRC=$(( f - sSRC ))
srcE=$(date -d "@$eSRC" -u +'%H:%M:%S')
if [ "$DIFFTIME" == "0" ]; then ENDTM=$ENDTM" file(s) created at: "$SRTTIME ; fi
{ echo ; echo ; }>> $2
if [ "$THETIME" == "noarguser" ]; then echo "Specified: "$argone "minutes" >> $2 ; else echo "Specified: "$argone "seconds" >> $2 ; fi
{ echo ; echo "Batch analysis and stats:"; } >> $2
echo -e $ST" Start" >> $2
echo -e $FN" Finish" >> $2
echo -e $srcE" Compile time" >> $2
echo "${ENDTM}"
}
