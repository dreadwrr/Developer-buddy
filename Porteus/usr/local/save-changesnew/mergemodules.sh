#!/usr/bin/env bash
# Merge modules                                                                                 01/09/2026
# only merges  *_uid_*.xzm  in $PWD extramod/ and only deletes the old on successful completion. skips _uid_L # also used for auto merging in /usr/local/bin/save-changesnew 
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
										# The script also renames them to .bak to avoid file name conflicts on the final save.
									
									# default true. Extract to /tmp as normal leave modules where they are as normal.
										
									# If set to false. First move the modules to /tmp first to free up space on what oculd be a usb drive. This can be an invaluable feature as if it had low
										# space can still merge
## End Diagnostics
# END CHANGABLE

#VARS
tmp=/mnt/live/tmp/atmp$$		;	ch=/mnt/live/memory/changes
elog=/tmp/error.log					;	INAME=/mnt/live/memory/images
oMF=/tmp/flog.log						;	QEXCL=/tmp/squashexfiles.log
mdlnames=()							;	candidates=()	
pst=$PWD			                        ;   output=""
targetem=$PWD
is_routine="false"						;	is_moved="false"

[[ -n "$1" ]] && [[ "$1" != "true" && "$1" != "false" ]] && echo "invalid argument function takes no arguments. one argument keepMRGED is only passed from /usr/local/bin/save-changesnew true false" && exit 1
[[ "$namingPRF" != "alpha" ]] && [[ "$namingPRF" != "numeric" ]] && echo "invalid setting namingPRF: $namingPRF" && exit 0
[[ "$1" != "" ]] && keepMRGED="$1" && is_routine="true"
ROLLBCK="$2"
ROLLSUMRY="$3"
archLMT="$4"
r=$( ls | grep '_uid_' | grep -v '_uid_L' | wc -l)  # ls -l | grep -c '_uid_[^L]' original  grep -c '.*_uid_.*.xzm',  original
if [ "$r" -gt 1 ]; then
	resolve_conflict "_uid_" "*.xzm" ".xzm" ".bak" $is_moved $oMF  # cds into /tmp or $output if moved
	if ! is_available "*_uid_*.xzm" $targetem "/mnt/live/tmp" $is_moved "true"; then exit 1 ; fi
    mkdir $tmp
	if [ "$ANALYTICS" == "true" ] && [ "$ANALYTICSECT" == "true" ]; then astart=$(date +%s.%N); fi
    unpack $tmp $QEXCL $oMF $elog $is_routine
	aend=$(date +%s.%N)
	if [ "$ANALYTICS" == "true" ]; then cyan "Modules merged. Packaging.." ; fi
	# in changes $ch
	cd $pst || exit 1  # back to extramod/
    SERIAL=`date +"%m-%d-%y_%R"|tr ':' '_'`
	[[ "$namingPRF" = "numeric" ]] && rand2d=$(rand_num)
	[[ "$namingPRF" = "alpha" ]] && rand2d=$(rand_alphauid)
	rname="${MODULENM}${SERIAL}_uid_${rand2d}$$.xzm"
	package_xzm $tmp $keepMRGED $elog $is_routine "false" $output
	is_rollback $tmp "_uid_" $ROLLBCK $ROLLSUMRY $archLMT $is_routine
	# General output. But not if called from save-changesnew
	if [[ "$is_routine" = "false" && "$ANALYTICS" = "true" ]]; then  [[ "$ANALYTICSECT" = "true" ]] && el=$(awk "BEGIN {print $aend - $astart}") && printf "Merge took %.3f seconds.\n" "$el" ; test -e $rname && { cyan "Moduled saved. in ${PWD}/" ; cyan $rname; } ; fi
    [[ "$is_routine" = "true" ]] && echo "${targetem}/${rname}" > /dev/shm/xsc
elif [ "$r" -eq 0 ]; then
	cyan "No modules detected or could be in the wrong working directory." && exit 0
else
	cyan "Only 1 module. exiting" && exit 0
fi
test -f $QEXCL && rm -f $QEXCL ; test -f $elog && rm -f $elog ; test -d "$tmp" && rm -rf "${tmp:?}"

