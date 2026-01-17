#!/usr/bin/env bash
# Merge changes modules _uid_xxxx to _uid_Lxxxx with deletions applied                          01/09/2026

. /usr/share/porteus/porteus-functions
get_colors
. /usr/local/save-changesnew/save-changesnewfnts
. /usr/local/save-changesnew/mergemodulesfunctions
if [[ $(whoami) != "root" ]]; then echo Please run script as root; exit; fi
# CHANGABLE
MODULENM="changes"        # the new name of merged .xzms

cmode="gzip"                            # default nothing. uses gzip compression level balanced
										   # xz        best compression
										   # zstd     faster bootup
											# lzo      faster bootup

namingPRF="alpha"				# default alpha 
												# numeric
# CHANGABLE BOOLEANS

ANALYTICS="true"			# display more verbose output

ANALYTICSECT="true"	# # disable metric saving time. ect. for ANALYTICS


keepMRGED="true"       # default is normally false but we want to rename all .xzms to .bak anyway
										# in this script regardless of preference


## Diagnostics
override="true"			# Note this only applies when keepMRGED is false. The script wont by default delete the modules first so if something goes wrong theres no change.
										# The script first renames them to .bak to avoid file name conflicts on the final save.
									
									# default true. Extract to /tmp leave modules where they are as normal.
										
									# If set to false. When keepMRGED is false First move the modules to /tmp to free up space on what oculd be a usb drive. This can be an invaluable feature as if it had low
										# space can still merge
## End Diagnostics
# END CHANGABLE

#VARS
tmp=/mnt/live/tmp/etmp$$			;	mtmp=/mnt/live/tmp/ntmp$$
ch=/mnt/live/memory/changes		;	INAME=/mnt/live/memory/images
msr="${PWD}/lscheck"					; 	oMF=/tmp/flog.log 
QEXCL=/tmp/squashexfiles.log		;   elog=/tmp/error.log
mdlnames=()								;	candidates=()
output=""										;   pst=$PWD	
targetem=$PWD
is_moved="false"							

f=$( ls $PWD | grep -c '.*_uid_L.*.xzm')
[[ "$f" -gt 1 ]] && echo "Cannot have more than one _uid_L\.\*\.xzm file" && exit 0
[[ "$f" -eq 1 ]] && read -r -p "merge will include previous L module continue? (y/n): " answer
[[ $answer == [Yy] ]] || { echo "rename prev mdl to .bak to continue" ; exit 0 ; }
if [ "$namingPRF" != "alpha" ] && [ "$namingPRF" != "numeric" ]; then echo "invalid setting namingPRF: $namingPRF" && exit 0 ; fi

r=$(ls | grep '.*_uid_.*\.xzm' | grep -v '_uid_L' | wc -l)
if [ "$r" -gt 0 ]; then
	resolve_conflict "_uid_L" "*.xzm" ".xzm" ".bak" $is_moved $oMF  # cds into /tmp ($output) if moved
	if ! is_available "*_uid_*.xzm" $targetem "/mnt/live/tmp" $is_moved; then exit 1 ; fi
    mkdir $mtmp
	if [ "$ANALYTICS" == "true" ] && [ "$ANALYTICSECT" == "true" ]; then astart=$(date +%s.%N); fi
	unpack $mtmp $QEXCL $oMF $elog "false"  # cds to changes $ch
	aend=$(date +%s.%N)
	if [ "$ANALYTICS" == "true" ]; then cyan "Modules merged. Packaging.." ; fi
	cd $pst || exit  # back to extramod/
	SERIAL=`date +"%m-%d-%y_%R"|tr ':' '_'`
	[[ "$namingPRF" = "numeric" ]] && ssbn=$(rand_num)
	[[ "$namingPRF" = "alpha" ]] && ssbn=$(rand_alpha)
	rname="${MODULENM}${SERIAL}_uid_L${ssbn}$$.xzm"
	package_xzm $mtmp $keepMRGED $elog "false" "false" $output
	xsize=$( du -sb "${PWD}/${rname}" | cut -f1)
	{ echo "bytes:"$xsize ; echo "file name:${rname}" ; echo ; } > $msr
	if [ "$ANALYTICS" == "true" ]; then [[ "$ANALYTICSECT" = "true" ]] && el=$(awk "BEGIN {print $aend - $astart}") && printf "Merge took %.3f seconds.\n" "$el" ; test -e "$rname" && { cyan "Moduled saved. in ${PWD}/" ; cyan $rname; } ; fi
elif [ "$r" -eq 0 ]; then
	cyan "No modules detected or could be in the wrong working directory." && exit 0
fi
test -f $elog && rm -f $elog ; test -f $QEXCL && rm -f $QEXCL ; test -d "$mtmp" && rm -rf "${mtmp:?}"
