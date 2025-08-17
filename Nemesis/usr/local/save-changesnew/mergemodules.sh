#!/bin/bash
# Merge modules                                                                                 08/01/2025
# Rename before making new file better practice
# Delete if all goes successful if keepMRGED false
# Added ROLLBCK from save-changesnew
#
#
# used for merging save-changesnew modules located in $BASEDIR/extramod     
#
# only merges  *_uid_*.xzm  in $PWD and only deletes the old on successful completion.
# the mode can be set to keep the old ones. As well as custom compression level
# processes changes relative to the modules
#


. /usr/share/porteus/porteus-functions
get_colors

#Check for root
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



#SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pst=$PWD    # save where we started

r=$( ls -l | grep -c '.*_uid_.*.xzm')
if [ "$r" -gt 1 ]; then
    mkdir $tmp
    > $oMF
    for mods in $PWD"/"*_uid_*.xzm; do 
         [[ "$mods" == *_uid_L* ]] && continue  # Skip files with _uid_L
        echo $mods >> $oMF #build the log of original list of modules names and paths

        dest="/mnt/loop-$(basename "$mods" .xzm)"
        mkdir $dest                   
    
        if mountpoint -q $dest; then echo "Error: $dest already mounted."; exit 1; fi
        if [ ! -f "$mods" ]; then echo "Error: Module file '$mods' not found."; exit 1; fi
        mount -o loop $mods $dest      #mount changes

        IFS="
        "
        cd $tmp || exit         # safer to cd into the directory
        for y in $(find "${dest}/" -name ".wh.*"); do  # process the .wh. on the merge
          f="$(echo $y | sed -e "s^${dest}/^^g" -e 's@\.wh\.@@g')"
          test -e "$f" && rm -rf "$f";
          test -e "$INAME/"*"/$f" || test -e "$y" && rm -f "$y"  # we are excluding the .wh.
                       #         ^   changed from "$INAME/*/$f"       to prevent binary operator expected on empty sym link
        done
        unset IFS
        # Remove conflicting whiteouts we have these files in place since the start of the script
        #for y in $(find $mtmp -name ".wh.*"); do
        #    f="$(echo "$y" | sed -e "s^$mtmp^^g" -e 's^\.wh\.^^g')"
        #    test -e "$f" && rm "$y";
        #done

        cp -aufv $dest/* $tmp 2> >(tee $elog >&2)      #unsquashfs -d $tmp $mods # xzm2dir $mods $tmp 
        if [ $? -ne 0 ]; then
            if grep -v '\.wh\.' $elog > /dev/null; then # more errors
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

        #using to avoid unsquashfs from err on .wh. lstat
        umount $dest
        rm -rf $dest
    done
    # we have no whiteouts because cp wont copy them but they are processed .wh..wh..opq wont be there because same
    cd $pst
    SERIAL=`date +"%m-%d-%y_%R"|tr ':' '_'`
    rand2d=$(printf "%02d" $((RANDOM % 100)))



    # rename before making new file
    if [ "$keepMRGED" == "true" ]; then #only from the original list of modules
        while IFS= read -r ofile; do #only from the original list of modules
            [[ -z "$ofile" || "$ofile" == \#* ]] && continue #skip blank line and comments
            fname=${ofile%.xzm}".bak"	 
            mv "$ofile" "$fname" #make them into .bak 
        done < "$oMF"
        unset IFS
    fi

    #dir2xzm $tmp "${PWD}/${MODULENM}${SERIAL}_uid_$$.xzm" 
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

    if [ "$keepMRGED" == "false" ]; then #succeeded 
        while IFS= read -r ofile; do
            [[ -z "$ofile" || "$ofile" == \#* ]] && continue #skip blank line and comments
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
