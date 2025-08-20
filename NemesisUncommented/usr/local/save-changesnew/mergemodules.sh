#!/bin/bash
# Merge modules                                                                                 08/01/2025
# only merges  *_uid_*.xzm  in $PWD and only deletes the old on successful completion.
. /usr/share/porteus/porteus-functions
get_colors
if [[ $(whoami) != "root" ]]; then echo Please run script as root; exit; fi
#VARS
tmp=/mnt/live/tmp/atmp$$
elog=/tmp/error.log
oMF=/tmp/flog.log               #original module name list used for merging

# CHANGABLE 
MODULENM="changes"        # the new name of merged .xzms

cmode="gzip"                            # default nothing. uses gzip compression level balanced
                                           # xz        best compression
                                           # zstd     faster bootup
                                            # lzo      faster bootup

# CHANGABLE BOOLEANS

keepMRGED="true"       # default is delete the old ones after merging

if [ "$1" != "" ]; then keepMRGED="$1"; fi
# END CHANGABLE
pst=$PWD
r=$( ls -l | grep -c '.*_uid_.*.xzm')
if [ "$r" -gt 1 ]; then
    mkdir $tmp
    > $oMF
    for mods in $PWD"/"*_uid_*.xzm; do 
         [[ "$mods" == *_uid_L* ]] && continue
        echo $mods >> $oMF

        dest="/mnt/loop-$(basename "$mods" .xzm)"
        mkdir $dest                   
    
        if mountpoint -q $dest; then echo "Error: $dest already mounted."; exit 1; fi
        if [ ! -f "$mods" ]; then echo "Error: Module file '$mods' not found."; exit 1; fi
        mount -o loop $mods $dest      #mount changes

        IFS="
        "
        cd $tmp || exit
        for y in $(find "${dest}/" -name ".wh.*"); do
          f="$(echo $y | sed -e "s^${dest}/^^g" -e 's@\.wh\.@@g')"
          test -e "$f" && rm -rf "$f";
          test -e "$INAME/*/$f" || test -e "$y" && rm -f "$y"
        done
        unset IFS

        cp -aufv $dest/* $tmp 2> >(tee $elog >&2)
        if [ $? -ne 0 ]; then
            if grep -v '\.wh\.' $elog > /dev/null; then
                if [ "$1" != "" ]; then echo Error processing one mdl $mods >> $elog; fi
                red "Error processing one of the modules ${mods}"
                cyan "Everything preserved. Check the script and try again."
                umount $dest
                rm -rf $dest
                rm $oMF
                rm -rf $tmp
                exit 1
            else
                cyan "White out file detected and processed"  >&2
            fi
        fi
        umount $dest
        rm -rf $dest
    done

    cd $pst
    SERIAL=`date +"%m-%d-%y_%R"|tr ':' '_'`
    rand2d=$(printf "%02d" $((RANDOM % 100)))

    if [ "$keepMRGED" == "true" ]; then
        while IFS= read -r ofile; do
            [[ -z "$ofile" || "$ofile" == \#* ]] && continue
            fname=${ofile%.xzm}".bak"	 
            mv "$ofile" "$fname"
        done < "$oMF"
        unset IFS
    fi

    mksquashfs $tmp "${PWD}/${MODULENM}${SERIAL}_uid_${$}${rand2d}.xzm" -comp $cmode
    if [ $? -ne 0 ]; then
        if [ "$1" != "" ]; then echo Error making new mdl: $mods >> $elog; fi    
        red "Error making the new module: ${MODULENM}${SERIAL}_uid_$$.xzm" >&2
        cyan "Everything preserved."
        rm $oMF
        rm -rf $tmp
        exit 1
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
		if [ "$3" == "true" ]; then
			find "$tmp" -type f -printf '%P\n' >> archive/_uid_/${MODULENM}${SERIAL}_uid_${$}${rand2d}.bak.txt
			echo >> archive/_uid_/${MODULENM}${SERIAL}_uid_${$}${rand2d}.bak.txt
		    BRAND=`date +"MDY_%m-%d-%y-TIME_%R"|tr ':' '_'`
    		echo $BRAND >> archive/_uid_/${MODULENM}${SERIAL}_uid_${$}${rand2d}.bak.txt
		fi
	fi
    if [ "$keepMRGED" == "false" ]; then
        while IFS= read -r ofile; do
            [[ -z "$ofile" || "$ofile" == \#* ]] && continue
            rm $ofile
        done < "$oMF"
        unset IFS
    fi
    rm $oMF   
elif [ "$r" -eq 0 ]; then
    cyan "No modules detected or could be in the wrong working directory." && exit 0
else
    cyan "Only 1 module. exiting" && exit 0
fi
test -e $elog && rm $elog
test -d $tmp && rm -rf $tmp
