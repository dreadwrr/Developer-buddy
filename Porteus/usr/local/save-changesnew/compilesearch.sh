#!/bin/bash
#										Compile Search - Detect system changes and build custom profile
# command: recentchanges compile
#
# Compile feature of recentchanges aka Developer buddy.     v3.0 07/24/2025
#
#
# Check system usage or recent usage in the last 90 seconds. as the user does random things we can capture it as well as previous actions to exclude.
# end result is to provide the user a .conf file to use to compare to recentchanges filters and tweak script to their system.
#
#
# Deep scan scans back 60 seconds and 300 seconds ahead. checks for differences. if there are differences past the filter it will output those in
# /home/user/.config/save-changesnew
#
# generates custom sed statements for the profile to drag and drop into recentchanges. This script lifts the /etc/ and /var/run filter from recent
# changes so you can see if those are needed. The idea here is lets find those directories and exclude them!
#
# Another feature is if a file doesnt exist ie a cache item it will replace the time with File Does Not Exist. so you can get an idea this is a cache
# directory. A high traffic location
#
# You can customize this script     ie deepscanFWR and BK  scanFWR   ect    This script also generator custome sed filters for  recentchanges.
# It outputs these files in     /home/user/.config/save-changesnew
#
# general notes:  the search results append the differential so its the full time backward and forward. the program parses the differential for user
# feedback and change detection.
#
#
# File output	xSysDifferences"$deltaDIFF"secondsxSearch	Total system changes from backwards to forwards. No diff file output. the program will warn user if there are differences from back to forward.
#
#				xSysDifferences"$deltaDIFF"secondsSeds
#
#				xCustomFilterProfile                 		What you should look to filter   ie they slipt paste the filters. Total from backwards to forwards. Differential appended
#
#				CustomFilterProfileSeds
#
#				xCustomFilterInstructions
#
# Also borred script features from various scripts on porteus forums
# working off of base save-changes script by
# Author: Brokenman <brokenman@porteus.org>
# Author: fanthom <fanthom@porteus.org>

# This script requires twos variable   $1 compile   $2 theuser
#
. /usr/share/porteus/porteus-functions
get_colors

#CHANGEABLE
platform="porteus"  #default nemesis    ie porteus
#Customize the search
deepscanBK=60		# Default 60    Change these for foward and back
deepscanFWR=300		# 300
scanBK=30			# 30
scanFWR=60			# 60
deltaDIFF=0	#dont change this
#CHANGEABLE BOOLEANS
cFILTER="false" # default false      actually create the filter
#END CHANGEABLE


if [ `whoami` != "root" ]; then
	echo "Please enter your root password below"
    su - -c "/usr/local/save-changesnew/compilesearch.sh $1 $2 $3"     #change this if you move the location of this script so it calls if not root
    exit
fi
xMODE=$1
if [ "$3" == "" ]; then
	echo "incorrect usage. compile username."; exit 1
fi
if [ "$2" == "" ]; then  #Default user
	USR="guest"
else
    USR=$2
fi

fixwh() { sed -e 's_ _\\ _g' -e 's_\/_\\\/_g' -e 's_\._\\\._g' -e 's_\]_\\]_g' -e 's_\[_\\[_g' -e 's_(_\\(_g' -e 's_)_\\)_g' ; }
fixOT() { sed -e 's_?_\\?_g'  -e 's_\^_\\^_g' -e 's_+_\\+_g' -e 's_*_\\*_g' -e 's_\$_\\$_g'  -e 's_\&_\\&_g' ; }

work=work$$											;		tmp=/tmp/work$$

RECENT=$tmp/list_recentchanges.txt					;  	RECENTTWO=$tmp/list_recentchgtwo.txt
COMPLETE=$tmp/list_complete.txt						;   COMPLETETWO=$tmp/list_compltwo.txt
SORTCOMPLETE=$tmp/list_complete_sorted.txt			;   SRTCOMPLETETWO=$tmp/list_srtcompletwo_sorted.txt
TMPCOMPLETE=$tmp/tmp_complete.txt					;   USRDIR=/home/$USR
UPDATE=$tmp/save.transferlog.tmp					;   moduleDIR=/CustomFilter$$
chxzm=/rntfiles.xzm									;	CONFIGDIR=/.config/save-changesnew
INSTRU="/xCustomFilterInstructions"					;	PRFLFLT=$tmp/list_sedfilters.txt

SNDRYDIR="false"									;	BASEDIR="false"
SYSCHG="false"										;	FLTCHG="false"
inputTIME="false"									;	inputSCAN="false"
inputSED="true"										;	validRLT="false"
diffRLT="false"



if [ $deepscanBK -lt 10 ] || [ $scanBK -lt 10 ]; then echo "unsupported time. please select number ge to 10"; exit 1; fi
if [ $deepscanBK -ge $deepscanFWR ] || [ $scanBK -ge $scanFWR ]; then echo Scan back is greater than scan forwards; exit 1; fi

echo "Deep scan [Y,n] ? "
read input
if [ "$input" == "Y" ] || [ "$input" == "y" ]; then
	inputSCAN="true"
    echo "Scanning back $deepscanBK seconds"
else
    echo  "Scanning back $scanBK seconds"
fi
echo "Show file times? [Y,n] ? "
read input
if [ "$input" == "Y" ] || [ "$input" == "y" ]; then
	inputTIME="true"
    echo "File times will be input"
else
	echo " will not show filetimes... "
    echo  "coming right up... "
fi
echo
echo "and finally generate sed filters [Y,n] ?"
read input
if [ "$input" == "N" ]  || [ "$input" == "n" ]; then
	inputSED="false"
    echo "you answered no setting saved."
else
	echo "custom sed filters will be made"

fi
echo
echo  "processing... "

mkdir $tmp

# If a desired time is specified we will search for that  (in seconds)
#check if the argument is a number
if [ "$xMODE" == "compile" ]; then

    p=60   # divider   to minutes

    if [[ "$inputSCAN" == "true" ]]; then
    	cyan   "Starting deep scan. scanning back $deepscanBK seconds. continue to use your machine as you normally would "
    	f=$deepscanBK # default 60 the backwards search
    	deltaDIFF=$(( deepscanFWR + deepscanBK ))  # Our delta forwards and back

    else
    	cyan   "Starting regular scan. scanning back $scanBK seconds. continue to use your machine as you normally would "
    	f=$scanBK 	# default 30
    	deltaDIFF=$(( scanFWR + scanBK ))
    fi

	tmn=$( echo "scale=2; $f /$p" | bc)
	if [ $(( $f % $p )) -eq 0 ]; then
		tmn=$(( $f / $p ))
	fi

    cyan   "searching back to get the delta"
    echo
	yellow " while this completes. Suggest grab a coffee   "
	cyan "searching for files" $f" seconds old or newer"
	#echo "scale=1; $1 /$p" | bc

	find /bin /etc /home /lib /lib64 /opt /root /sbin /usr /var -mmin -"$tmn" -not -type d |tee $COMPLETE > /dev/null 2> /dev/null

else
    echo not intended use of compile feature. exiting
    exit
fi

cyan "preliminary sample complete.                     "
cyan "         Scanning delta"$deltaDIFF" <--------->  "
echo

if [[ "$inputSCAN" == "true" ]]; then
	c=$deepscanFWR           # default 300       #How long do you want to search for?
else
	c=$scanFWR        # default 60
fi

tmn=$( echo "scale=2; $c /$p" | bc)
if [ $(( $c % $p )) -eq 0 ]; then
	tmn=$(( $c / $p ))
fi

echo "please wait $tmn minutes. continue to use your computer like you normally would."
echo
echo "modify this script for a custom time"
totalTIME=$c
sleep $c
p=60

find /bin /etc /home /lib /lib64 /opt /root /sbin /usr /var -mmin -"$tmn" -not -type d |tee $COMPLETETWO > /dev/null 2> /dev/null

if [[ "$inputTIME" == "true" ]]; then

 	while IFS= read x; do
 		f=$(stat -c '%Y' "$x" 2> /dev/null);

 		theDATE=$( date -d "@$f" +'%Y-%m-%d %H:%M:%S' 2> /dev/null)
 		if [ "${f}" == "" ] || [ "${theDATE}" == "" ]; then
   		 	theDATE="Filedoes notexist"
		fi
 		h=$theDATE
 		test -e "$x" && { test -f "$x" && echo $h "$x" || echo "FILEDOES -NOTEXIST" "$x"; } >> $SORTCOMPLETE; done < $COMPLETE

 	while IFS= read x; do
 		f=$(stat -c '%Y' "$x" 2> /dev/null);

 		theDATE=$( date -d "@$f" +'%Y-%m-%d %H:%M:%S' 2> /dev/null)
 		if [ "${f}" == "" ] || [ "${theDATE}" == "" ]; then
   		 	theDATE="Filedoes notexist"
		fi
		h=$theDATE
 		test -e "$x" && { test -f "$x" && echo $h "$x" || echo "FILEDOES -NOTEXIST" "$x"; } >> $SRTCOMPLETETWO; done < $COMPLETETWO
    else
  		while IFS= read x; do test -e "$x" &&  { test -f "$x" && echo "$x" || echo "FILEDOES -NOTEXIST" "$x"; } >> $SORTCOMPLETE; done < $COMPLETE
		while IFS= read x; do test -e "$x" &&  { test -f "$x" && echo "$x" || echo "FILEDOES -NOTEXIST" "$x"; } >> $SRTCOMPLETETWO; done < $COMPLETETWO
    fi
unset IFS

cp $SORTCOMPLETE $RECENT
cp $SRTCOMPLETETWO $RECENTTWO

#Filtering new to version 3 call filter
/usr/local/save-changesnew/filter $RECENT $USR $RECENTTWO

#If you comment out a line ie a Secondary dir. set SNDRYDIR to true  example /var/run is uncommented so SNDRYDIR is false
if grep -Fq "^/var/run/" $RECENT; then
    if ! grep -Fq "^/var/run/" $RECENTTWO; then
        SNDRYDIR="false"
    fi
fi

# repeat above for another important secondary that you might filter

#  Now we get into the important directories. Do we exclude at the risk of deleting our program? Tread carefully
#  Very carefully select only starting /etc/    <------  We can remove this filter if needed
# we dont want  /etc/
# /etc is commented in filter so we set it to true
 if grep -Fq "^/etc" $RECENT; then
    if grep -Fq "^/etc" $RECENTTWO; then
        BASEDIR="true"      # example /etc is commented so BASEDIR is true #not filtering /etc    it is not filtered
    fi
fi

# repeat above for important basedir if you commented it out in filter

#Inclusions from this script
sed -i '/\/usr\/local\/save-changesnew/d' $RECENT $RECENTTWO

# End of filtering

sort -o $RECENT $RECENT
sort -o $RECENTTWO $RECENTTWO
sort -o $SORTCOMPLETE $SORTCOMPLETE
sort -o $SRTCOMPLETETWO $SRTCOMPLETETWO

#We have a log of all system changes $COMPLETETWO will include that

# Do log everything

BRAND=`date +"MDY_%m-%d-%y-TIME_%R"|tr ':' '_'`

test -e $USRDIR$CONFIGDIR || mkdir --parents $USRDIR$CONFIGDIR
cd $USRDIR$CONFIGDIR

localDIR=$( echo $moduleDIR | sed "s|^/||g")

pflNM="xCustomFilterProfile"


# Move any old xCustomFilterProfile -->   /home/guest/.config/save-changesnew/ files   also any          xSysDifferences"$deltaDIFF"seconds to new folder
test -e $USRDIR$CONFIGDIR$INSTRU && { mkdir $USRDIR$CONFIGDIR$moduleDIR ; mv $pflNM* $localDIR 2> /dev/null ; mv "xSysDifferences"* $localDIR 2> /dev/null; mv "CustomFilterProfile"* $localDIR 2> /dev/null;  mv $USRDIR$CONFIGDIR$INSTRU $localDIR;  }


#test -e $USRDIR$CONFIGDIR$"/"$pflNM && { mkdir $USRDIR$CONFIGDIR$moduleDIR ; mv $pflNM* $localDIR 2> /dev/null ; mv "xSysDifferences"* $localDIR 2> /dev/null; mv "CustomFilterProfile"* $localDIR 2> /dev/null; test -e $USRDIR$CONFIGDIR$INSTRU && mv $USRDIR$CONFIGDIR$INSTRU $localDIR;  }
# Move old xCustomFilterDiff to new fold
#test -e $USRDIR$CONFIGDIR$ModuleDIR && { mv $pflNM* $localDIR 2> /dev/null; }

#rm $USRDIR$CONFIGDIR"/*" 2> /dev/null

# UNFILTERED sorted handle the difference no need to show user the difference. Just append last search to old search send back
# $SORTCOMPLETE
#  $SRTCOMPLETETWO
diffFile=$tmp"/xSysUnfiltered"$deltaDIFF"seconds"

test -e $SRTCOMPLETETWO && { test -e $SORTCOMPLETE && comm -13 $SORTCOMPLETE $SRTCOMPLETETWO > $diffFile; }

if [ ! -s $diffFile ]; then
    #echo difference empty
	test -e $diffFile && rm $diffFile

	echo $BRAND >> $SORTCOMPLETE
	cp $SORTCOMPLETE $USRDIR$CONFIGDIR"/xSysDifferences"$deltaDIFF"secondsxSearch"
else
	# We set a limit of 4 files to define a system change
	d=$( grep -c ^ $diffFile)

	if (( $d >= 10 )); then SYSCHG="true"; fi
	echo $BRAND >> $diffFile

	# Is the file empty?
	k=$( head -n1 $diffFile | grep "MDY")

	if [ ! -n "$k" ]; then

		#echo difference not empty
		# append unique differences, sort and back to sortcomplete
    	cat $diffFile >> $SORTCOMPLETE
    	sort -o $SORTCOMPLETE $SORTCOMPLETE
    	echo xSysDifferences$deltaDIFF"xSearch is total unfiltered system changes. The total differences" >> $USRDIR$CONFIGDIR$INSTRU
    	echo "exactly what has changed. " >> $USRDIR$CONFIGDIR$INSTRU
    	echo >> $USRDIR$CONFIGDIR$INSTRU

    	cp $SORTCOMPLETE $USRDIR$CONFIGDIR"/xSysDifferences"$deltaDIFF"secondsxSearch"
	fi
fi

# Generate sys sed filters
if [[ "$inputSED" == "true" ]]; then

    echo >> $USRDIR$CONFIGDIR$INSTRU
	echo "xSysDifferences"$deltaDIFF"secondsSeds are drag and drop into recent changes. " >> $USRDIR$CONFIGDIR$INSTRU
	echo " so you can review either and add some new filters     " >> $USRDIR$CONFIGDIR$INSTRU
	echo >> $USRDIR$CONFIGDIR$INSTRU

	# generate seds for system
	if [[ "$inputTIME" == "true" ]]; then
		awk '{print $3}' $SORTCOMPLETE > $TMPCOMPLETE
	else
		awk '{print $1}' $SORTCOMPLETE > $TMPCOMPLETE
    fi
   	sed -i 's![^/]*$!!' $TMPCOMPLETE  # delete anything after last occurance of / on line
   	sed -i 's/\/$//' $TMPCOMPLETE  # replace /  at end of line
	cat $TMPCOMPLETE | fixwh | fixOT > $PRFLFLT
	sed -i '$d' $PRFLFLT  # remove last line of file the date
	sed -i "s/^/sed -i '\//g" $PRFLFLT  # append start   sed -i '/
	sed -i "s/$/\/d'/g" $PRFLFLT     #append end    /d'
	awk '!seen[$0]++' $PRFLFLT > $TMPCOMPLETE ; cat $TMPCOMPLETE > $PRFLFLT #remove duplicate line occurances with awk and send back
	echo $BRAND >> $PRFLFLT
	cp $PRFLFLT $USRDIR$CONFIGDIR"/xSysDifferences"$deltaDIFF"secondsSeds"
fi
# END of UNFILTERED processing


#	FILTERED 	$RECENT	$RECENTTWO
# Begin of FILTERED
diffFileTwo=$tmp"/xCustomFilterProfile"

test -e $RECENTTWO && { test -e $RECENT && comm -13 $RECENT $RECENTTWO > $diffFileTwo; }

# FILTERED actual files that made it past the filtering

if [ ! -s $diffFileTwo ]; then
	test -e $diffFileTwo && rm $diffFileTwo
	echo $BRAND >> $RECENT

	echo "xCustomFilterProfile you had no diffs. Nothing from the "$totalTIME" second search " >> $USRDIR$CONFIGDIR$INSTRU
	echo " made it past the filters. This was the active search" >> $USRDIR$CONFIGDIR$INSTRU
	echo >> $USRDIR$CONFIGDIR$INSTRU
	#No changes send old search
	cp $RECENT $USRDIR$CONFIGDIR"/xCustomFilterProfile"
else
	echo $BRAND >> $diffFileTwo

	# We set a limit of 4 files to make it paste the filters.
	d=$( grep -c ^ $diffFileTwo)

	if (( $d >= 4 )); then
		FLTCHG="true"
	fi
	if (( $d == 1)); then
		echo "only 1 file made it paste the filters. the delta"
	fi
	if [ ! -n "$d" ]; then
		echo "break runtime error"
		exit 1
	fi

	echo "xCustomFilterProfile is what you should look at" >> $USRDIR$CONFIGDIR$INSTRU
	echo "for your filters in recent changes. " >> $USRDIR$CONFIGDIR$INSTRU
	echo " this is the important file         " >> $USRDIR$CONFIGDIR$INSTRU
	echo " In otherwords this file combines   " >> $USRDIR$CONFIGDIR$INSTRU
	echo " the differential of what made it   " >> $USRDIR$CONFIGDIR$INSTRU
	echo " past the filters                   " >> $USRDIR$CONFIGDIR$INSTRU
	echo >> $USRDIR$CONFIGDIR$INSTRU
	# Is the file empty?
	k=$( head -n1 $diffFileTwo | grep "MDY")

	if [ ! -n "$k" ]; then
		echo " You had deltas in the search and they were appended " >> $USRDIR$CONFIGDIR$INSTRU
		echo "to xCustomFilterProfile" >> $USRDIR$CONFIGDIR$INSTRU

		#Append diffs to old search and build filter profile
		cat $diffFileTwo >> $RECENT
		sort $RECENT > $TMPCOMPLETE ; mv $TMPCOMPLETE $RECENT

	else  #The difference file is empty
		#rm $diffFileTwo
		diffRLT="true"
		echo $BRAND >> $RECENT
		echo "You had no deltas During the search no new files made it past the filters"
	fi

	#These are all files that slipt paste the filter. User should review.
	cp $RECENT $USRDIR$CONFIGDIR"/xCustomFilterProfile"
fi

#check if the xCustomFilterProfile is empty
i=$( head -n1 $RECENT | grep "MDY")

if [ -n "$i" ]; then
	validRLT="true"
	test -f $USRDIR$CONFIGDIR"/xCustomFilterProfile" && rm $USRDIR$CONFIGDIR"/xCustomFilterProfile"
	echo "xCustomFilterProfile is empty. Success nothing at all made it past the " >> $USRDIR$CONFIGDIR$INSTRU
	echo "current filters." >> $USRDIR$CONFIGDIR$INSTRU
fi

# Generate custom sed filters for user
if [ "$inputSED" == "true" ]; then

    sort $RECENT | uniq -c | sort -n | awk '{print $2}' > $TMPCOMPLETE     # New to version 3 sort only profile seds
    cat $TMPCOMPLETE > $RECENT

	if [[ "$inputTIME" == "true" ]]; then
		awk '{print $3}' $RECENT > $TMPCOMPLETE
	else
		awk '{print $1}' $RECENT > $TMPCOMPLETE
    fi

    echo "Note these are sorted by highest count first" >> $TMPCOMPLETE
    echo >> $TMPCOMPLETE

   	sed -i 's![^/]*$!!' $TMPCOMPLETE  # delete anything after last occurance of /  on line
   	sed -i 's/\/$//' $TMPCOMPLETE  # replace /  at end of line
	cat $TMPCOMPLETE | fixwh | fixOT > $PRFLFLT
	sed -i '$d' $PRFLFLT  # remove last line of file  the timestamp
	sed -i "s/^/sed -i '\//g" $PRFLFLT  # append start and put in  sed -i '/
	sed -i "s/$/\/d'/g" $PRFLFLT     #append end of file   /d'


    #awk '!seen[$0]++' $PRFLFLT > $TMPCOMPLETE ; cat $TMPCOMPLETE > $PRFLFLT  #remove duplicate lines with awk and send back
	echo $BRAND >> $PRFLFLT
	cp $PRFLFLT $USRDIR$CONFIGDIR"/CustomFilterProfileSeds"
fi

echo " Thank you for using Developer buddy. " >> $USRDIR$CONFIGDIR$INSTRU
echo >> $USRDIR$CONFIGDIR$INSTRU
echo " if you see any bugs please let me know " >> $USRDIR$CONFIGDIR$INSTRU
# END of FILTERED processing

# Logging complete
#cleanup
rm -rf $tmp

cyan " Custom filter complete.	"
echo

if [ "$BASEDIR" == "true" ]; then
cyan "   including basedir   /etc"
echo
cyan " if your compiler outputs here change recentchanges"
cyan " filter.     This script lifts  /etc  and /var/run filter"
cyan " so you can verify if you need to exclude"
echo
fi
if [ "$SNDRYDIR" == "true" ]; then
cyan "   including secondary dir  /var/run"
cyan " same as above verify recentchanges filter ..."
echo
fi
if [ "$FLTCHG" == "true" ]; then
purple " Success please review your xCustomerFilterProfile"
cyan "     in    "$USRDIR$CONFIGDIR"/xCustomFilterProfile"
purple " change in deltas detected"
else
cyan " Filter change boolean indicates you dont need to  change "
cyan "your filter.  ie less than 4 files made it past the filter"
echo
fi
if  [ "$SYSCHG" == "true" ]; then
yellow " Warn system changed from earlier ensure sterile enviro"
else
cyan " System didnt change during the search"
echo
fi
if [ "$validRLT" == "true" ]; then
blue " Success no files made it past the filters"
cyan "during the "$deltaDIFF" second search. The delta"
fi
if [ "$diffRLT" == "true" ]; then
echo
purple " You had no differences in the"$deltaDIFF" search"
purple " Nothing made it paste the filters  during this time."
echo
fi
cyan " Search results in "$USRDIR$CONFIGDIR
