#!/bin/bash
# Merge changes modules _uid_xxxx to _uid_Lxxxx with deletions applied                          07/18/2025
. /usr/share/porteus/porteus-functions
get_colors
. /usr/local/save-changesnew/save-changesnewfnts
if [[ $(whoami) != "root" ]]; then echo Please run script as root; exit; fi
# CHANGABLE
MODULENM="changes"        # the new name of merged .xzms

cmode="gzip"                            # default nothing. uses gzip compression level balanced
                                           # xz        best compression
                                           # zstd     faster bootup
                                            # lzo      faster bootup
# CHANGABLE BOOLEANS
keepMRGED="true"       # default is normally false but we want to rename all .xzms to .bak anyway
                                        # in this script regardless of preference
# END CHANGABLE
tmp=/mnt/live/tmp/etmp$$		; mtmp=/mnt/live/tmp/ntmp$$
ch=/mnt/live/memory/changes	; INAME=/mnt/live/memory/images
#EXCL=/tmp/squashexfiles.log		; EXFILES=/tmp/squashregex
msr="${PWD}/lscheck"				; oMF=/tmp/flog.log 
pst=$PWD
f=$( ls -l ${PWD}${em} | grep -c '.*_uid_L.*.xzm')
if [ "$f" -gt 1 ]; then
    echo "Cannot have more than one _uid_L\.\*\.xzm file" && exit 0
fi
r=$(ls -1 | grep '.*_uid_.*\.xzm' | grep -v '_uid_L' | wc -l)
if [ "$r" -gt 0 ]; then
    mkdir $mtmp
    > $oMF ; x=0
    unpack $mtmp
#    cd $ch || exit
#    find $mtmp -name ".wh.*" -printf '%P\0' | while IFS= read -r -d '' y; do
#        f="${y#$mtmp}"
#        f="${f//.wh./}"
#        test -e "$f" && rm "$y"
#    done
#    unset IFS
    if [ "$keepMRGED" == "true" ]; then
        while IFS= read -r ofile; do
            [[ -z "$ofile" || "$ofile" == \#* ]] && continue
                fname=${ofile%.xzm}".bak"
                mv "$ofile" "$fname"
        done < "$oMF"
        unset IFS
    fi
    SERIAL=`date +"%m-%d-%y_%R"|tr ':' '_'` ; ssbn=$(rand_alpha)
    rand2d=$(printf "%02d" $((RANDOM % 100)))
    rname="${MODULENM}${SERIAL}_uid_L${ssbn}${$}${rand2d}.xzm"
    mksquashfs $mtmp "${PWD}/${rname}" -comp $cmode
    if [ $? -ne 0 ]; then
        red "Error making the new module: ${rname}" >&2
        cyan "Everything preserved."
        rm $oMF
        #rm $EXCL
        #rm $EXFILES
        rm -rf $mtmp
        exit 1
    fi
    if [ "$keepMRGED" == "false" ]; then
        while IFS= read -r ofile; do
            [[ -z "$ofile" || "$ofile" == \#* ]] && continue
            test -f $ofile && rm $ofile
        done < "$oMF"
        unset IFS
    fi
    xsize=$( du -sb "${PWD}/${rname}" | cut -f1)
    echo "bytes:"$xsize > $msr
    echo "file name:${rname}" >> $msr
    echo >> $msr
    rm $oMF
    #rm $EXCL
    #rm $EXFILES
    rm -rf $mtmp
elif [ "$r" -eq 0 ]; then
    cyan "No modules detected or could be in the wrong working directory." && exit 0
fi
