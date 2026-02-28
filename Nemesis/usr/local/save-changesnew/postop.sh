#!/usr/bin/env bash
#   Developer buddy 5.0                                               01/14/2026
# POSTOP
. /usr/share/porteus/porteus-functions
get_colors
SCRIPT_PATH="$( dirname "$0")"
. "$SCRIPT_PATH"/rntchangesfunctions
atmp=$(mktemp -d /tmp/tmpda.XXXXXX)
xdata=$atmp/xdata
k1="$1"
USRDIR="$2"
# toml=$3
# if [ -f $USRDIR/doctrine.tsv ]; then
#     sed -i 's/^POSTOP = true/POSTOP = false/' $toml
# else
# rnul=$( basename $k1)
[[ -f "$k1" ]] && mv $k1 $xdata || exit 1  
printf 'Datetime\tFile\tSize(kb)\tType\tSymlink\tTarget\tChange_time\tcam\tAccessed\tOwner\tStatable\tCopy\n' > $atmp/doctrine
while IFS= read -r x || [ -n "$x" ]; do
	mtyp=""
    sym=""
    tgt=""
	cam=""
    stbool=""
	copy=""
	size_kb=0
	IFS=' ' read -r f1 f2 f3 f4 f5 f6 f7 f8 f9 _ f11 _ _ f14 f15 <<< "$x"
	[[ -z "$f15" ]] && continue
	dt="$f1 $f2"
	chgtime="$f3 $f4"
	at="$f5 $f6"
	if [ "$f7" -ge 0 ] 2>/dev/null; then size_kb=$(( f7 / 1024 )); fi
	is_sym=$f8
	onr=$f9
	#ggp=$f10
	is_cam=$f11
	# lmod="$f12 $f13"
	is_copy="$f14"
	y="$f15"
	filepath="$( unescf "$y")"
	if [ -f "$filepath" ]  || [ -L "$filepath" ]; then
        [[ "$is_sym" == "y" ]] && sym="y"
		sz=$(stat --format="%s" "$filepath" 2>/dev/null)
		if [ -n "$sz" ]; then
            [[ "$sym" = "y" ]] && { tgt=$( readlink "$filepath") || tgt="${tgt:-N/A}" ; }  # if [ -L "$filepath" ]; then sym="y"; fi
			stbool="y"
			size_kb=$(( sz / 1024 ))
			mtyp=$( file --brief --mime-type "$filepath")
			if [ "$mtyp" == "application/octet-stream" ]; then mtyp="Unknown"; fi
		fi
		if [ "$is_cam" == "y" ]; then cam="y" ; fi
		if [ "$is_copy" == "y" ]; then copy="y" ; fi
        printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$dt" "$y" "$size_kb" "$mtyp" "$sym" "$tgt" "$chgtime" "$cam" "$at" "$onr" "$stbool" "$copy" >> $atmp/doctrine
	fi
done < $xdata
unset IFS
head -1 $atmp/doctrine > $USRDIR/doctrine.tsv
tail -n +2 "$atmp/doctrine" | sort -t$'\t' -k10,10 -k3,3n >> "$USRDIR/doctrine.tsv"
green "File doctrine.tsv created in $USRDIR"
# #column -t -s $'\t' $USRDIR/doctrine.tsv      this command prints a nice tab seperated log
test -d "$atmp" && rm -rf "${atmp:?}"
