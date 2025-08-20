#!/bin/bash
# Merge changes modules _uid_xxxx to _uid_Lxxxx with deletions applied                          07/18/2025
. /usr/share/porteus/porteus-functions
get_colors
if [[ $(whoami) != "root" ]]; then echo Please run script as root; exit; fi
rand_alpha() {
  letters=( {A..Z} {a..z} )
  echo -n "${letters[RANDOM % 52]}${letters[RANDOM % 52]}"
}
fixsqh() {  sed -e 's|^/||'; }
#VARS
tmp=/mnt/live/tmp/etmp$$         ; mtmp=/mnt/live/tmp/ntmp$$
ch=/mnt/live/memory/changes     ; INAME=/mnt/live/memory/images
msr="${PWD}/lscheck"

# Any files to exclude                      #  only if we have to escape for regex
EXCL=/tmp/squashexfiles.log        ;  EXFILES=/tmp/squashregex     
oMF=/tmp/flog.log               #original module name list used for removing or renaming after merging

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
pst=$PWD
f=$( ls -l ${PWD}${em} | grep -c '.*_uid_L.*.xzm')
if [ "$f" -gt 1 ]; then
    echo "Cannot have more than one _uid_L\.\*\.xzm file" && exit 0
fi
r=$(ls -1 | grep '.*_uid_.*\.xzm' | grep -v '_uid_L' | wc -l)
if [ "$r" -gt 0 ]; then
    mkdir $mtmp
    > $EXCL ; > $EXFILES ; > $oMF
    for mods in $PWD"/"*_uid_*.xzm; do
     
        [[ "$mods" == *_uid_L* ]] && continue
        echo $mods >> $oMF

        dest="/mnt/loop-$(basename "$mods" .xzm)"
        mkdir $dest         

        if mountpoint -q $dest; then echo "Error: $dest already mounted. Everything preserved."; exit 1; fi
        if [ ! -f "$mods" ]; then echo "Error: Module file $mods. Check the script and try again"; exit 1; fi
        mount -o loop $mods $dest      #mount changes

        IFS="
        "
        cd $mtmp || exit
        for y in $(find "${dest}/" -name ".wh.*"); do
          f="$(echo $y | sed -e "s^${dest}/^^g" -e 's@\.wh\.@@g')"
          test -e "$f" && rm -rf "$f";
          test -e "$INAME/*/$f" || { echo "y" | fixsqh >> $EXCL; echo "$y" >> $EXFILES; test -e "$y" && rm -f "$y"; }
        done
        unset IFS

        cp -aufv $dest/* $mtmp 2> >(tee /tmp/error.log >&2)
        if [ $? -ne 0 ]; then
            if grep -v '\.wh\.' /tmp/error.log > /dev/null; then
                red "Error processing one of the modules ${mods}"
                cyan "Everything preserved. Check the script and try again. check /tmp/error.log"
                umount $dest
                rm -rf $dest
                rm $oMF
                rm $EXCL
                rm $EXFILES
                rm -rf $mtmp
                exit 1
            else
                cyan "White out file detected and processed"  >&2
            fi
        fi
        umount $dest
        rm -rf $dest
    done

    cd $ch
    find $mtmp -name ".wh.*" -printf '%P\0' | while IFS= read -r -d '' y; do
        f="${y#$mtmp}"           
        f="${f//.wh./}"           
        test -e "$f" && rm "$y"
    done
    unset IFS

    cd $mtmp
    find . -name ".wh.*" -exec rm -r {} \;

    cd $pst

    if [ "$keepMRGED" == "true" ]; then 
        while IFS= read -r ofile; do
            [[ -z "$ofile" || "$ofile" == \#* ]] && continue
                fname=${ofile%.xzm}".bak"     
                mv "$ofile" "$fname"
        done < "$oMF"
        unset IFS
    fi
             
    SERIAL=`date +"%m-%d-%y_%R"|tr ':' '_'`

    ssbn=$(rand_alpha)
    rand2d=$(printf "%02d" $((RANDOM % 100)))
    rname="${MODULENM}${SERIAL}_uid_L${ssbn}${$}${rand2d}.xzm"

    mksquashfs $mtmp "${PWD}/${rname}" -comp $cmode -ef $EXCL
    if [ $? -ne 0 ]; then
        red "Error making the new module: ${rname}" >&2
        cyan "Everything preserved."
        rm $oMF
        rm $EXCL
        rm $EXFILES
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
    rm $EXCL
    rm $EXFILES
    rm -rf $mtmp
else
    cyan "No modules detected or could be in the wrong working directory." && exit 0
fi
