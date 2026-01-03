#!/bin/bash
# Merge on drive. custom method for merging with xzm2dir. od stands for on drive or overdrive.       12/28/2025
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


keepMRGED="false"       # default is delete the old ones after merging



## Diagnostics
override="false"			# Note this only applied when keepMRGED is false.

									# default false. Move the modules to tmp to free up space on the drive.

									# true. You dont want them sent to /tmp first and the feature is overridden.
	
									# this script implements logic to ensure there is free space when merging modules on the drive because porteus could be installed on a usb. 
									# The override setting was put in so if set to true would make it strictly hdd and no shift.
## End Diagnostics
# END CHANGABLE

#VARS
workdir=/work$$						;	xopt=/mnt/live/tmp/atmp$$	# spare tmp fld
tmp=$PWD$workdir					;	elog=/tmp/error.log					
QEXCL=/tmp/squashexfiles.log	;	INAME=/mnt/live/memory/images
mdlnames=()							;	candidates=()	
pst=$PWD									;	ng_state=$(shopt -p nullglob)
targetem=$PWD						;	oMF=/tmp/flog.log	
shopt -s nullglob
output=""									;	is_moved="false"

if [ "$ANALYTICS" == "true" ]; then [[ "$ANALYTICSECT" = "true" ]] && echo in ; fi
exit
[[ "$namingPRF" != "alpha" ]] && [[ "$namingPRF" != "numeric" ]] && echo "invalid setting namingPRF: $namingPRF" && exit 0
if [ "$1" != "" ]; then keepMRGED="$1"; fi

r=$( ls | grep '.*.xzm' | wc -l)
if [ "$r" -gt 1 ]; then
	resolve_conflict "false" "*.xzm" ".xzm" ".bak"  # cds into /tmp ($output) if moved
	if ! is_available "*.xzm" $targetem $PWD $is_moved; then exit 1 ; fi
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
		            test -d $tmp && rm -rf $tmp
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
		if [[ -n "$y" && -n "$x" ]] && (( y < x)); then rm -rf "$p" ; fi
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

