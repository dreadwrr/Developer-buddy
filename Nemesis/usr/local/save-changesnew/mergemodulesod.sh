#!/usr/bin/env bash
# Merge on drive. custom method for merging with xzm2dir. od stands for on drive or overdrive.       01/09/2026
# Merges 2 or more modules on the drive to handle .wh. files after merging. Doesnt use /tmp because .wh. cant be copied or stated unless mounted. 
#
# How it works. Merge the modules in a /tmp folder in PWD or extramod. Afterwards stat the .wh. files and if the .wh. file is newer
# than the file then delete it. Doesnt require a bunch of loops and mounting to handle the deletions.
#
# premise if keepMRGED is false, move all candidate .xzm to /tmp named to .bak. To avoid possible prompts of you dont have enough space.
# so take action and make space. Do the work if something goes wrong the modules are in tmp to be recovered. 
#
# thought about adding mdlMRGSECT="false" which is equivalent to FEEDBACK="false" to supress unsquashfs -q but these file operations
# is a good idea not to supress anything especially merging.
#
# try to merge modules efficiently and effectively for merging of any module. and only deletes the old on successful completion.
. /usr/share/porteus/porteus-functions
get_colors
. /usr/local/save-changesnew/save-changesnewfnts
. /usr/local/save-changesnew/mergemodulesfunctions
if [[ $(whoami) != "root" ]]; then echo Please run script as root; exit; fi
# CHANGABLE
MODULENM="changes"        # prefix for merged .xzms

cmode="gzip"                            # default nothing. uses gzip compression level balanced
                                           # xz        best compression
                                           # zstd     faster bootup
                                            # lzo      faster bootup

namingPRF="alpha"				# default alpha 
												# numeric

# CHANGABLE BOOLEANS

ANALYTICS="true"			# display more verbose output

ANALYTICSECT="true"	# # disable metric saving time. ect. for ANALYTICS


keepMRGED="true"       # default is delete the old ones after merging



## Diagnostics
override="true"			# Note this only applies when keepMRGED is false. 

									# default false. Move the modules first to tmp to free up space on the drive.

									# true. You dont want them sent to /tmp first and the feature is overridden.
	
									# this script implements logic to ensure there is free space when merging modules on the drive because porteus could be installed on a usb. 


d2dmdl="true"				# use the harddrive or usb for temp all files/work. if having a problem like extracting to tmp set this to true to use the drive
									# true extract in extramod. default 
									# false extract as normal to tmpfs in live system 

									# The script wont by default delete the modules first so if something goes wrong theres no change
									# The override and d2dmdl settings were put in because of imbalance of free space for different configurations
## End Diagnostics
# END CHANGABLE

#VARS
workdir=/work$$						;	xopt=/mnt/live/tmp/atmp$$	# spare tmp fld
tmp=$PWD$workdir					;	INAME=/mnt/live/memory/images
elog=/tmp/error.log					;	oMF=/tmp/flog.log	
QEXCL=/tmp/squashexfiles.log	;	passdir=$PWD  # passdir is aka PWD
mdlnames=()							;	pst=$PWD
candidates=()							;	targetem=$PWD							
ng_state=$(shopt -p nullglob) 	;	shopt -s nullglob

output=""									;	is_moved="false"



if [[ "$d2dmdl" = "false" ]]; then [[ -d /mnt/live/tmp ]] && tmp=/mnt/live/tmp/atmp$$ && passdir="/mnt/live/tmp" || echo "no tmpfs using default tmp folder $tmp" ; fi

[[ "$namingPRF" != "alpha" ]] && [[ "$namingPRF" != "numeric" ]] && echo "invalid setting namingPRF: $namingPRF" && exit 0
if [ "$1" != "" ]; then keepMRGED="$1"; fi

r=$( ls | grep '.*.xzm' | wc -l)
if [ "$r" -gt 1 ]; then
	resolve_conflict "false" "*.xzm" ".xzm" ".bak"  # cds into /tmp ($output) if moved

	if ! is_available "*.xzm" $targetem $passdir $is_moved; then exit 1 ; fi
    mkdir $tmp
	if [ "$ANALYTICS" == "true" ] && [ "$ANALYTICSECT" == "true" ]; then astart=$(date +%s.%N); fi
    # Unpack
	for mods in "${PWD}/"*.xzm; do
		# [[ -z "$fname" ]] && fname="$mods" hold the first name of the merge
        fname="$mods"
		for candidate in "${candidates[@]}"; do
		    if [ "$candidate" == "$mods" ]; then
		        if ! unsquashfs -no-exit -f -dest $tmp "$mods"; then
		            [[ -f "$oMF" ]] && rm $oMF
		            test -d "$tmp" && rm -rf "$tmp"
		            red "Error failure to extract in ${PWD}: ${fname} to target $tmp" >&2
		            cyan "Everything preserved. Check the script"
		            exit 1
		        fi
		        break
		    fi
		done
	done
	cd $tmp || exit
	# if a .wh. is newer after merged delete the file
	:> $QEXCL
	while IFS= read -r -d '' file; do
		y=""
       	p=${file/.wh./}  # $( echo "$file" | sed -E 's|(.*\/)\.wh\.|\1|')
		test -e "$p" && y=$( stat -c '%Y' "$p" 2>/dev/null)  # file
        x=$( stat -c '%Y' "$file" 2>/dev/null)  # .wh. 
		if [[ -n "$y" && -n "$x" ]] && (( y < x )); then rm -rf "$p" ; fi
		found="false"
		cand=( "$INAME"/*/"$p" )
		if ((${#cand[@]})); then found="true" ; fi
		[[ "$found" == "true" ]] || { echo "$file" | fixsqh >> $QEXCL; test -e "$file" && rm -f "$file"; }  # exclude and remove the .wh.  file. ensure its not included
    done < <(find . -type f -name '.wh.*' -printf '%P\0')
    unset IFS  
	#  Because this is just merging modules this step isnt necessary. It just sees if the file is in changes and if so removes the .wh. in the image.
	#	IFS="
	#	"
	#    cd $ch || exit
	#    # Remove conflicting whiteouts    If changes exit is implemented
	#    for y in $(find $tmp -name ".wh.*"); do 
	#        f="${y#$tmp}"           
	#        f="${f//.wh./}"           
	#        test -e "$f" && rm "$y"
	#    done
	#    unset IFS
	#
	#	cd $tmp || exit
	#	find . -name ".wh.*" -exec rm -r {} \;  # changes exit isnt fully implemented nemesis so could remove any remaining .wh. to delete all .wh. files from the merge
	$ng_state  # end Unpack
	aend=$(date +%s.%N)
	if [ "$ANALYTICS" == "true" ]; then cyan "Modules merged. Packaging.." ; fi
	cd $pst || exit  # in $tmp change back to extramod/
    SERIAL=`date +"%m-%d-%y_%R"|tr ':' '_'`
	[[ "$namingPRF" = "numeric" ]] && rand2d=$(rand_num)
	[[ "$namingPRF" = "alpha" ]] && rand2d=$(rand_alphauid)
	rname="${MODULENM}${SERIAL}_uid_${rand2d}$$.xzm"
	package_xzm $tmp $keepMRGED $elog "false" "false" $output
    if [ "$ANALYTICS" == "true" ]; then [[ "$ANALYTICSECT" = "true" ]] && el=$(awk "BEGIN {print $aend - $astart}") && printf "Merge took %.3f seconds.\n" "$el" ; test -e "$rname" && { cyan "Moduled saved. in ${PWD}/" ; cyan $rname; } ; fi
elif [ "$r" -eq 0 ]; then
	cyan "No modules detected or could be in the wrong working directory." && exit 0
else
	cyan "Only 1 module. exiting" && exit 0
fi
test -f $QEXCL && rm -f $QEXCL ; test -f $elog && rm -f $elog ; test -d "$tmp" && rm -rf "${tmp:?}"
# Notes quick reference
#k=$( echo "$file" | sed -e 's@.*/@@')   # grabs the filename from the path
