#!/bin/bash                  
#	Compile Search - Detect system changes and build custom profile  v3.0 07/24/2025    
# Also borred script features from various scripts on porteus forums
# working off of base save-changes script by
# Author: Brokenman <brokenman@porteus.org>
# Author: fanthom <fanthom@porteus.org>
. /usr/share/porteus/porteus-functions
get_colors
. /usr/local/save-changesnew/comp

#CHANGEABLE
platform="nemesis"  #default nemesis    ie porteus
#Customize the search																
deepscanBK=60   # Default 60    Change these for foward and back      
deepscanFWR=300 # 300												    
scanBK=30 # 30
scanFWR=60 # 60						
deltaDIFF=0	 #dont change this
#CHANGEABLE BOOLEANS
cFILTER="false" # default false      actually create the filter 
#END CHANGEABLE

if [ `whoami` != "root" ]; then
	echo "Please enter your root password below"
    su - -c "/usr/local/save-changesnew/compilesearch.sh $1 $2 $3"     #change this if you move the location of this script so it calls if not root
    exit
fi
if [ "$3" == "" ]; then echo "incorrect usage. compile username."; exit 1; fi
if [ "$2" == "" ]; then USR="guest"; else USR=$2; fi
fixwh() { sed -e 's_ _\\ _g' -e 's_\/_\\\/_g' -e 's_\._\\\._g' -e 's_\]_\\]_g' -e 's_\[_\\[_g' -e 's_(_\\(_g' -e 's_)_\\)_g' ; }
fixOT() { sed -e 's_?_\\?_g'  -e 's_\^_\\^_g' -e 's_+_\\+_g' -e 's_*_\\*_g' -e 's_\$_\\$_g'  -e 's_\&_\\&_g' ; }
tmp=/tmp/work$$													;   work=work$$
xMODE=$1
RECENT=$tmp/list_recentchanges.txt						;  	RECENTTWO=$tmp/list_recentchgtwo.txt
COMPLETE=$tmp/list_complete.txt							;   COMPLETETWO=$tmp/list_compltwo.txt
SORTCOMPLETE=$tmp/list_complete_sorted.txt  	;   SRTCOMPLETETWO=$tmp/list_srtcompletwo_sorted.txt
TMPCOMPLETE=$tmp/tmp_complete.txt              	;   USRDIR=/home/$USR
UPDATE=$tmp/save.transferlog.tmp		            	;   moduleDIR=/CustomFilter$$
chxzm=/rntfiles.xzm								    			;	CONFIGDIR=/.config/save-changesnew
INSTRU="/xCustomFilterInstructions"				    	;	PRFLFLT=$tmp/list_sedfilters.txt		
SNDRYDIR="false"													;	BASEDIR="false"	
SYSCHG="false"														;	FLTCHG="false"
inputTIME="false"													;	inputSCAN="false"	
inputSED="true"														;   validRLT="false"					 					
diffRLT="false"
if [ $deepscanBK -lt 10 ] || [ $scanBK -lt 10 ]; then echo "unsupported time. please select number ge to 10"; exit 1; fi
if [ $deepscanBK -ge $deepscanFWR ] || [ $scanBK -ge $scanFWR ]; then echo Scan back is greater than scan forwards; exit 1; fi
echo "Deep scan [Y,n] ? "
read input
if [ "$input" == "Y" ] || [ "$input" == "y" ]; then
	inputSCAN="true"
    echo "Scanning back $deepscanBK seconds "
else
    echo  "Scanning back $scanBK seconds "
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
echo "                                   "
echo "and finally generate sed filters [Y,n] ?"
read input
if [ "$input" == "N" ]  || [ "$input" == "n" ]; then
	inputSED="false"
	echo "                             "
    echo "you answered no setting saved." 
else
	echo "custom sed filters will be made"
	 
fi
echo "                               "
echo  "processing... "
mkdir $tmp
if [ "$xMODE" == "compile" ]; then
    
    if [[ "$inputSCAN" == "true" ]]; then
    	cyan   "Starting deep scan. scanning back $deepscanBK seconds. continue to use your machine as you normally would "
    	f=$deepscanBK
    	deltaDIFF=$(( deepscanFWR + deepscanBK ))
    	
    else
    	cyan   "Starting regular scan. scanning back $scanBK seconds. continue to use your machine as you normally would "
    	f=$scanBK               
    	deltaDIFF=$(( scanFWR + scanBK )) 
    fi 
    comp $f
    cyan    "searching back to get the delta"
    cyan    "                               "    
	cyan     " while this completes. Suggest grab a coffee   "
	cyan    "searching for files" $f" seconds old or newer" 

	find /bin /etc /home /lib /lib64 /opt /root /sbin /usr /var -mmin "-"$qtn -not -type d 2> /dev/null |tee $COMPLETE > /dev/null 2> /dev/null

else
    echo not intended use of compile feature. exiting
    exit
fi

cyan "preliminary sample complete.                     "
cyan "         Scanning delta"$deltaDIFF" <--------->  "
cyan "                                                 "

if [ "$inputSCAN" == "true" ]; then        
	c=$deepscanFWR
else
	c=$scanFWR
fi
comp $c

echo "please wait $qtn minutes. continue to use your computer like you normally would."
echo "                                         "
echo "modify this script for a custom time"
totalTIME=$c
sleep $c

find /bin /etc /home /lib /lib64 /opt /root /sbin /usr /var -mmin -"$qtn" -not -type d 2> /dev/null |tee $COMPLETETWO > /dev/null 2> /dev/null

if [ ! -s $COMPLETETWO ]; then
	    echo aborting scan. system didnt change nothing to compare to. ; exit 1
fi

if [ "$inputTIME" == "true" ]; then

 	while IFS= read -r x || [ -n "$x" ]; do 
 		f=$(stat -c '%Y' "$x" 2> /dev/null);
 		
 		theDATE=$( date -d "@$f" +'%Y-%m-%d %H:%M:%S' 2> /dev/null)
 		if [ "${f}" == "" ] || [ "${theDATE}" == "" ]; then
   		 	theDATE="Filedoes notexist"
		fi	
 		h=$theDATE
 		test -e "$x" && { echo $h "$x" || echo "FILEDOES -NOTEXIST" "$x"; } >> $SORTCOMPLETE; done < $COMPLETE
 		
 	while IFS= read -r x || [ -n "$x" ]; do 
 		f=$(stat -c '%Y' "$x" 2> /dev/null);
 		
 		theDATE=$( date -d "@$f" +'%Y-%m-%d %H:%M:%S' 2> /dev/null)
 		if [ "${f}" == "" ] || [ "${theDATE}" == "" ]; then
   		 	theDATE="Filedoes notexist"
		fi 				
		h=$theDATE
 		test -e "$x" && { echo $h "$x" || echo "FILEDOES -NOTEXIST" "$x"; } >> $SRTCOMPLETETWO; done < $COMPLETETWO
    else
  		while IFS= read x; do test -e "$x" &&  { test -f "$x" && echo "$x" || echo "FILEDOES -NOTEXIST" "$x"; } >> $SORTCOMPLETE; done < $COMPLETE   
		while IFS= read x; do test -e "$x" &&  { test -f "$x" && echo "$x" || echo "FILEDOES -NOTEXIST" "$x"; } >> $SRTCOMPLETETWO; done < $COMPLETETWO   
    fi  
unset IFS


cp $SORTCOMPLETE $RECENT
cp $SRTCOMPLETETWO $RECENTTWO

/usr/local/save-changesnew/filter $RECENT $USR $RECENTTWO 

if grep -Fq "^/var/run/" $RECENT; then
    if ! grep -Fq "^/var/run/" $RECENTTWO; then
        SNDRYDIR="false"
    fi
fi

 if grep -Fq "^/etc" $RECENT; then
    if grep -Fq "^/etc" $RECENTTWO; then
        BASEDIR="true"      # example /etc is commented so BASEDIR is true #not filtering /etc    it is not filtered 
    fi
fi

sed -i '/\/usr\/local\/save-changesnew/d' $RECENT $RECENTTWO #Inclusions from this script

sort $RECENT > $TMPCOMPLETE ; mv $TMPCOMPLETE $RECENT
sort $RECENTTWO > $TMPCOMPLETE ; mv $TMPCOMPLETE $RECENTTWO
sort $SORTCOMPLETE > $TMPCOMPLETE ; mv $TMPCOMPLETE $SORTCOMPLETE
sort $SRTCOMPLETETWO > $TMPCOMPLETE ; mv $TMPCOMPLETE $SRTCOMPLETETWO

BRAND=`date +"MDY_%m-%d-%y-TIME_%R"|tr ':' '_'`
test -e $USRDIR$CONFIGDIR || mkdir --parents $USRDIR$CONFIGDIR
cd $USRDIR$CONFIGDIR
localDIR="${moduleDIR#/}"
pflNM="xCustomFilterProfile"

# Move
test -e $USRDIR$CONFIGDIR$INSTRU && { mkdir $USRDIR$CONFIGDIR$moduleDIR ; mv $pflNM* $localDIR 2> /dev/null ; mv "xSysDifferences"* $localDIR 2> /dev/null; mv "CustomFilterProfile"* $localDIR 2> /dev/null;  mv $USRDIR$CONFIGDIR$INSTRU $localDIR;  }

diffFile=$tmp"/xSysUnfiltered"$deltaDIFF"seconds"
test -e $SRTCOMPLETETWO && { test -e $SORTCOMPLETE && comm -13 $SORTCOMPLETE $SRTCOMPLETETWO > $diffFile; }
if [ ! -s $diffFile ]; then
	test -e $diffFile && rm $diffFile
	echo $BRAND >> $SORTCOMPLETE
	cp $SORTCOMPLETE $USRDIR$CONFIGDIR"/xSysDifferences"$deltaDIFF"secondsxSearch"
else
	d=$( grep -c ^ $diffFile)
	if (( d >= 10 )); then
		SYSCHG="true"
	fi
	
	echo $BRAND >> $diffFile
	
	k=$( head -n1 $diffFile | grep "MDY")
	if [ -z "$k" ]; then

    	cat $diffFile >> $SORTCOMPLETE
    	sort $SORTCOMPLETE > $TMPCOMPLETE ; mv $TMPCOMPLETE $SORTCOMPLETE
    	echo xSysDifferences$deltaDIFF"xSearch is total unfiltered system changes. The total differences" >> $USRDIR$CONFIGDIR$INSTRU
    	echo "exactly what has changed. " >> $USRDIR$CONFIGDIR$INSTRU
    	echo "                                               " >> $USRDIR$CONFIGDIR$INSTRU
   
    	cp $SORTCOMPLETE $USRDIR$CONFIGDIR"/xSysDifferences"$deltaDIFF"secondsxSearch"	
	fi
fi
if [[ "$inputSED" == "true" ]]; then 	
    	
    echo "                                         " >> $USRDIR$CONFIGDIR$INSTRU
	echo "xSysDifferences"$deltaDIFF"secondsSeds are drag and drop into recent changes. " >> $USRDIR$CONFIGDIR$INSTRU
	echo " so you can review either and add some new filters     " >> $USRDIR$CONFIGDIR$INSTRU
	echo "                                                  " >> $USRDIR$CONFIGDIR$INSTRU
    	
	if [[ "$inputTIME" == "true" ]]; then 
		awk '{print $3}' $SORTCOMPLETE > $TMPCOMPLETE
	else
		awk '{print $1}' $SORTCOMPLETE > $TMPCOMPLETE   	
    fi
   	sed -i 's![^/]*$!!' $TMPCOMPLETE
   	sed -i 's/\/$//' $TMPCOMPLETE
	cat $TMPCOMPLETE | fixwh | fixOT > $PRFLFLT
	sed -i '$d' $PRFLFLT
	sed -i "s/^/sed -i '\//g" $PRFLFLT
	sed -i "s/$/\/d'/g" $PRFLFLT
	awk '!seen[$0]++' $PRFLFLT > $TMPCOMPLETE ; cat $TMPCOMPLETE > $PRFLFLT
	echo $BRAND >> $PRFLFLT
	cp $PRFLFLT $USRDIR$CONFIGDIR"/xSysDifferences"$deltaDIFF"secondsSeds"			
fi
diffFileTwo=$tmp"/xCustomFilterProfile"

test -e $RECENTTWO && { test -e $RECENT && comm -13 $RECENT $RECENTTWO > $diffFileTwo; }
if [ ! -s $diffFileTwo ]; then
	test -e $diffFileTwo && rm $diffFileTwo
	echo $BRAND >> $RECENT

	echo "xCustomFilterProfile you had no diffs. Nothing from the "$totalTIME" second search " >> $USRDIR$CONFIGDIR$INSTRU
	echo " made it past the filters. This was the active search" >> $USRDIR$CONFIGDIR$INSTRU
	echo "                                               " >> $USRDIR$CONFIGDIR$INSTRU
	cp $RECENT $USRDIR$CONFIGDIR"/xCustomFilterProfile"
else	
	echo $BRAND >> $diffFileTwo
	d=$( grep -c ^ $diffFileTwo)
	if (( d >= 4 )); then
		FLTCHG="true"
	fi
	if (( d == 1)); then
		echo "only 1 file made it paste the filters. the delta"
	fi	
	if [ -z "$d" ]; then
		echo "break runtime error"
		exit 1
	fi

	echo "xCustomFilterProfile is what you should look at" >> $USRDIR$CONFIGDIR$INSTRU
	echo "for your filters in recent changes. " >> $USRDIR$CONFIGDIR$INSTRU
	echo " this is the important file         " >> $USRDIR$CONFIGDIR$INSTRU	
	echo " In otherwords this file combines   " >> $USRDIR$CONFIGDIR$INSTRU
	echo " the differential of what made it   " >> $USRDIR$CONFIGDIR$INSTRU
	echo " past the filters                   " >> $USRDIR$CONFIGDIR$INSTRU
	echo "                                    " >> $USRDIR$CONFIGDIR$INSTRU		

	k=$( head -n1 $diffFileTwo | grep "MDY")
	
	if [ -z "$k" ]; then
		echo " You had deltas in the search and they were appended " >> $USRDIR$CONFIGDIR$INSTRU
		echo "to xCustomFilterProfile" >> $USRDIR$CONFIGDIR$INSTRU
				
		cat $diffFileTwo >> $RECENT
		sort $RECENT > $TMPCOMPLETE ; mv $TMPCOMPLETE $RECENT
	    
	else 
		diffRLT="true"
		echo $BRAND >> $RECENT
		echo "You had no deltas During the search no new files made it past the filters"
		
	fi

	cp $RECENT $USRDIR$CONFIGDIR"/xCustomFilterProfile"
fi
i=$( head -n1 $RECENT | grep "MDY")
if [ -n "$i" ]; then
	validRLT="true"
	test -f $USRDIR$CONFIGDIR"/xCustomFilterProfile" && rm $USRDIR$CONFIGDIR"/xCustomFilterProfile"
	echo "xCustomFilterProfile is empty. Success nothing at all made it past the " >> $USRDIR$CONFIGDIR$INSTRU
	echo "current filters." >> $USRDIR$CONFIGDIR$INSTRU
fi

# Generate custom sed filters for user
if [ "$inputSED" == "true" ]; then

    sort $RECENT | uniq -c | sort -n | awk '{print $2}' > $TMPCOMPLETE
    cat $TMPCOMPLETE > $RECENT

	if [[ "$inputTIME" == "true" ]]; then 
		awk '{print $3}' $RECENT > $TMPCOMPLETE
	else
		awk '{print $1}' $RECENT > $TMPCOMPLETE   	
    fi

    echo "Note these are sorted by highest count first" >> $TMPCOMPLETE
    echo >> $TMPCOMPLETE 
   	sed -i 's![^/]*$!!' $TMPCOMPLETE 
   	sed -i 's/\/$//' $TMPCOMPLETE
	cat $TMPCOMPLETE | fixwh | fixOT > $PRFLFLT
	sed -i '$d' $PRFLFLT
	sed -i "s/^/sed -i '\//g" $PRFLFLT
	sed -i "s/$/\/d'/g" $PRFLFLT
	echo $BRAND >> $PRFLFLT
	cp $PRFLFLT $USRDIR$CONFIGDIR"/CustomFilterProfileSeds"
fi
echo " Thank you for using Developer buddy. " >> $USRDIR$CONFIGDIR$INSTRU	
echo "                                     " >> $USRDIR$CONFIGDIR$INSTRU
echo " if you see any bugs please let me know " >> $USRDIR$CONFIGDIR$INSTRU
rm -rf $tmp
cyan " Custom filter complete.	"
cyan "                          "
if [ "$BASEDIR" == "true" ]; then
cyan "   including basedir   /etc                       		"
echo "                                                          "
cyan " if your compiler outputs here change recentchanges 		"
cyan " filter.     This script lifts  /etc  and /var/run filter "
cyan " so you can verify if you need to exclude					"
cyan "                                                          "
fi
if [ "$SNDRYDIR" == "true" ]; then
cyan "   including secondary dir  /var/run                  	"
cyan " same as above verify recentchanges filter ...        	"
cyan "															"
fi
if [ "$FLTCHG" == "true" ]; then
cyan " Success please review your xCustomerFilterProfile      "
cyan "     in    "$USRDIR$CONFIGDIR"/xCustomFilterProfile       "
cyan " change in deltas detected                              "
else
cyan " Filter change boolean indicates you dont need to  change "
cyan "your filter.  ie less than 4 files made it past the filter"
cyan "															"
fi
if  [ "$SYSCHG" == "true" ]; then								 	
green " Warn system changed from earlier ensure sterile enviro	"
else
cyan " System didnt change during the search					"
cyan " 													   		"
fi
if [ "$validRLT" == "true" ]; then
cyan " Success no files made it past the filters                "
cyan "during the "$deltaDIFF" second search. The delta          "

fi
if [ "$diffRLT" == "true" ]; then
purple " 													    "
purple " You had no differences in the"$deltaDIFF" search       "
purple " Nothing made it paste the filters  during this time.   "
purple "														"
fi
cyan " Search results in "$USRDIR$CONFIGDIR"                    "
