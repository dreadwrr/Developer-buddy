#!/bin/bash
# Merge changes modules _uid_xxxx to _uid_Lxxxx with deletions applied                          07/18/2025
# used for creating a compatible linked state module to use with save-changesnew version 3 
# these would be in $BASEDIR/extramod     
#
# only merges  *_uid_*.xzm  in $PWD and only deletes the old on successful completion.
# the mode can be set to keep the old ones. As well as custom compression level
# processes changes relative to the modules and the current session. Removes all .wh. for now after
#


. /usr/share/porteus/porteus-functions
get_colors

#Check for root
if [[ $(whoami) != "root" ]]; then echo Please run script as root; exit; fi

# random serial generating function
rand_alpha() {
  letters=( {A..Z} {a..z} )
  echo -n "${letters[RANDOM % 52]}${letters[RANDOM % 52]}"
}

# Fix EXCL to work with mksquashfs exclusion file
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



#SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pst=$PWD # save this

f=$( ls -l ${PWD}${em} | grep -c '.*_uid_L.*.xzm')
if [ "$f" -gt 1 ]; then
    echo "Cannot have more than one _uid_L\.\*\.xzm file" && exit 0
fi

r=$(ls -1 | grep '.*_uid_.*\.xzm' | grep -v '_uid_L' | wc -l) #if compgen -G "*_uid_*.xzm" > /dev/null; then

if [ "$r" -gt 0 ]; then
    #mkdir $tmp
    mkdir $mtmp
   
    > $EXCL
    > $EXFILES 
    #pst=$PWD # save this
    #cd $tmp
    > $oMF
    for mods in $PWD"/"*_uid_*.xzm; do # we know there is at least one so dont need shpglob to not iterate over the pattern if no files
     
        [[ "$mods" == *_uid_L* ]] && continue  # Skip files with _uid_L

        #mkdir $mtmp # temporary staging
        echo $mods >> $oMF #build the log of original list of modules names and paths

        dest="/mnt/loop-$(basename "$mods" .xzm)"
        mkdir $dest         

        if mountpoint -q $dest; then echo "Error: $dest already mounted. Everything preserved."; exit 1; fi
        if [ ! -f "$mods" ]; then echo "Error: Module file $mods. Check the script and try again"; exit 1; fi
        mount -o loop $mods $dest      #mount changes

        IFS="
        "
        cd $mtmp || exit         # safer to cd into the directory
        for y in $(find "${dest}/" -name ".wh.*"); do  # process the .wh. on the merge
          f="$(echo $y | sed -e "s^${dest}/^^g" -e 's@\.wh\.@@g')"
          test -e "$f" && rm -rf "$f";
          test -e "$INAME/"*"/$f" || { echo "y" | fixsqh >> $EXCL; echo "$y" >> $EXFILES; test -e "$y" && rm -f "$y"; }  # we are excluding the .wh.
                       #         ^   changed from "$INAME/*/$f"       to prevent binary operator expected on empty sym link   
        done
        unset IFS

        cp -aufv $dest/* $mtmp 2> >(tee /tmp/error.log >&2)      #unsquashfs -d $tmp $mods # xzm2dir $mods $tmp 
        if [ $? -ne 0 ]; then
            if grep -v '\.wh\.' /tmp/error.log > /dev/null; then
                red "Error processing one of the modules ${mods}"
                cyan "Everything preserved. Check the script and try again. check /tmp/error.log"
                umount $dest
                rm -rf $dest
                rm $oMF
                rm $EXCL
                rm $EXFILES
                #rm -rf $tmp
                rm -rf $mtmp
                exit 1
            else
                cyan "White out file detected and processed"  >&2
            fi
        fi

        #using to avoid unsquashfs from err on .wh. lstat
        umount $dest
        rm -rf $dest
    done

    #  Only should be handled in actual main save-changesnew  .wh..wh..opq
    # check for an opq files and delete the layer below from the files already merged
    #find $mtmp -type f -name '.wh..wh..opq' -printf '%P\0' | while IFS= read -r -d '' file; do
        #p=$( echo "$file" | sed -E 's|(.*\/)\.wh\.\.wh\.\.opq\.|\1|')  # removes .wh..wh..opq from start of file keeps full path 
    #    p=$( echo "$file" | sed -e 's![^/]*$!!') # drops to the root directory of the .wh..wh..opq file   /thisdir/thatdir/myfile.txt   returns  /thisdir/thatdir/ 
    #    [[ ! -z "$(find $tmp -mindepth 1 -print -quit)" ]] && test -e $p && rm -rf $p        # we have to drop one directory and not do this if its the first .xzm
    #    rm $file # remove the opq         <--------- mtmp is missing ....    it wont allow us to copy it anyway
    #done
    #unset IFS

    # Merge into the tmp files
    #cp -a $mtmp/* $tmp  # merge the contents into the directories
    #rm -rf $mtmp  # remove our temporary staging for the module we just merged

    ### delete .wh. files where applicable ###
    #find . -type f -name '.wh.*' -printf '%P\n'

    # we want to resolve any .wh. between merged not from our current session.
#    find . -type f -name '.wh.*' -printf '%P\0' | while IFS= read -r -d '' file; do
        #k=$( echo "$file" | sed -e 's@.*/@@')   # grabs the filename from the path
        #p=$(echo "$k" | sed 's/^\.wh\.//')  # strip the .wh. from start our file or directory name
#        p=$( echo "$file" | sed -E 's|(.*\/)\.wh\.|\1|') # same thing but with path in it 
#        x=$( stat -c '%Y' "$file") # get modified date of .wh. file
  
#        rsl=""
#        test -e "$p" && { y=$( stat -c '%Y' "$p"); if (( y < x)); then rsl="true"; rm -rf "$p"; fi; } # if the .wh. is newer after merged we check and delete # || { test -d $p && y=$( stat -c '%Y' "$p"); if (( y < x)); then rsl="true"; test -z "$(find $file -mindepth 1 -print -quit)" && rm -r $p; fi; }
#        test -e "$INAME/"*"/$p" || { echo "$file" | fixsqh >> $EXCL; echo "$file" >> $EXFILES; test -e "$file" && rm -f "$file"; }     # excluse and remove the .wh.  file
#    done

#    unset IFS

    cd $ch

    # Remove conflicting whiteouts    If changes exit is implemented
    find $mtmp -name ".wh.*" -printf '%P\0' | while IFS= read -r -d '' y; do   #     for y in $(find . -name ".wh.*" -printf '%P\0'); do
        f="${y#$mtmp}"           
        f="${f//.wh./}"           
        #f="${y/.wh./}" # f="$(echo "$y" | sed -e 's^\.wh\.^^g')" f="$(echo "$y" | sed -e "s^$mtmp^^g" -e 's^\.wh\.^^g')"
        test -e "$f" && rm "$y" # remove the .wh.
    done
    unset IFS

    cd $mtmp
    find . -name ".wh.*" -exec rm -r {} \; # changes exit isnt fully implemented so remove any remaining .wh. for now. 

    cd $pst     # return to original working directory


    # rename before transfering files
    if [ "$keepMRGED" == "true" ]; then 
        while IFS= read -r ofile; do #from the original list of modules
            [[ -z "$ofile" || "$ofile" == \#* ]] && continue #skip blank line and comments
                fname=${ofile%.xzm}".bak"     
                mv "$ofile" "$fname" #make them into .bak 
        done < "$oMF"
        unset IFS
    fi
             
    SERIAL=`date +"%m-%d-%y_%R"|tr ':' '_'`

    ssbn=$(rand_alpha)
    rand2d=$(printf "%02d" $((RANDOM % 100)))
    rname="${MODULENM}${SERIAL}_uid_L${ssbn}${$}${rand2d}.xzm"
    #dir2xzm $tmp "${PWD}/${MODULENM}${SERIAL}_uid_$$.xzm" 

    mksquashfs $mtmp "${PWD}/${rname}" -comp $cmode -ef $EXCL
    if [ $? -ne 0 ]; then
        red "Error making the new module: ${rname}" >&2
        cyan "Everything preserved."
        rm $oMF
        rm $EXCL
        rm $EXFILES
        rm -rf $mtmp
        #rm -rf $tmp
        exit 1
    fi
    if [ "$keepMRGED" == "false" ]; then # Succeeded we can now delete old if option set
        while IFS= read -r ofile; do # only delete from the original list of modules
            [[ -z "$ofile" || "$ofile" == \#* ]] && continue #skip blank line and comments
            test -f $ofile && rm $ofile
        done < "$oMF"
        unset IFS
    fi
    
    # create a msr file             
    xsize=$( du -sb "${PWD}/${rname}" | cut -f1) # byte size        
    echo "bytes:"$xsize > $msr # used for linking the next L module
    echo "file name:${rname}" >> $msr # new serial
    echo >> $msr # space to denote end 
   
    rm $oMF 
    rm $EXCL # clean up
    rm $EXFILES
    rm -rf $mtmp
else
    cyan "No modules detected or could be in the wrong working directory." && exit 0
fi
