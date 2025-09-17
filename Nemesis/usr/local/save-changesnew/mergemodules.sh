#!/bin/bash
# Merge modules                                                                                 08/01/2025
# only merges  *_uid_*.xzm  in $PWD and only deletes the old on successful completion.
. /usr/share/porteus/porteus-functions
get_colors
. /usr/local/save-changesnew/save-changesnewfnts
if [[ $(whoami) != "root" ]]; then echo Please run script as root; exit; fi
#VARS
tmp=/mnt/live/tmp/atmp$$ ; elog=/tmp/error.log
oMF=/tmp/flog.log              
# CHANGABLE
MODULENM="changes"        # the new name of merged .xzms

cmode="gzip"                            # default nothing. uses gzip compression level balanced
                                           # xz        best compression
                                           # zstd     faster bootup
                                            # lzo      faster bootup
# CHANGABLE BOOLEANS
keepMRGED="true"       # default is delete the old ones after merging
# END CHANGABLE
if [ "$1" != "" ]; then keepMRGED="$1"; fi
pst=$PWD
r=$( ls -l | grep -c '.*_uid_.*.xzm')
if [ "$r" -gt 1 ]; then
    mkdir $tmp ; > $oMF ; x=0
    unpack $tmp
    SERIAL=`date +"%m-%d-%y_%R"|tr ':' '_'`
    rand2d=$(printf "%02d" $((RANDOM % 100)))
    while IFS= read -r ofile; do [[ -z "$ofile" || "$ofile" == \#* ]] && continue ; fname="$( basename "${ofile%.xzm}").bak" ; mv "$ofile" "/tmp/$fname" ; done < "$oMF"
    unset IFS
    mksquashfs $tmp "${PWD}/${MODULENM}${SERIAL}_uid_${$}${rand2d}.xzm" -comp $cmode
    if [ $? -ne 0 ]; then
        if [ "$1" != "" ]; then echo Error making new mdl: $mods >> $elog; fi
        red "Error making the new module: ${MODULENM}${SERIAL}_uid_$$.xzm" >&2
        cyan "Modules are in /tmp."
        rm $oMF ; rm -rf $tmp ; exit 1
    fi
	if [ "$2" == "true" ] && [ "$1" != "" ]; then
		if [ -d archive/_uid_ ]; then
			r=$(find archive/_uid_ -maxdepth 1 -type f -name '*.bak' 2>/dev/null | wc -l)
			if [ "$r" -ge "$4" ]; then
				for mods in archive/_uid_/*_uid_*.bak; do
					rm -f $mods
					test -f $mods".txt" && rm $mods".txt"
					break
				done
			fi
		else
			mkdir -p archive/_uid_
		fi
		cp ${MODULENM}${SERIAL}_uid_${$}${rand2d}.xzm archive/_uid_/${MODULENM}${SERIAL}_uid_${$}${rand2d}.bak
		[[ "$3" == "true" ]] && BRAND=`date +"MDY_%m-%d-%y-TIME_%R"|tr ':' '_'` && { find "$tmp" -type f -printf '%P\n' ; echo ; echo $BRAND ; } >> archive/_uid_/${MODULENM}${SERIAL}_uid_${$}${rand2d}.bak.txt
	fi
    while IFS= read -r ofile; do [[ -z "$ofile" || "$ofile" == \#* ]] && continue ; fname="$( basename "${ofile%.xzm}").bak" ; [[ "$keepMRGED" == "true" ]] && cmd=(mv "/tmp/$fname" "$PWD") || cmd=(rm "/tmp/$fname") ; "${cmd[@]}" ; done < "$oMF"
	unset IFS
    rm $oMF
elif [[ "$r" -eq 0 ]]; then
    cyan "No modules detected or could be in the wrong working directory." && exit 0 
else
    cyan "Only 1 module. exiting" && exit 0
fi
test -e $elog && rm $elog ; test -d $tmp && rm -rf $tmp
exit
