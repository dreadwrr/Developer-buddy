#!/bin/bash
#   Developer buddy 3.0 core                                               11/19/2025
# POSTOP
. /usr/share/porteus/porteus-functions
get_colors
. /usr/local/save-changesnew/rntchangesfunctions
atmp=$(mktemp -d /tmp/tmpda.XXXXXX)
xdata=$atmp/xdata
k1="$1"
[[ -f "$k1" ]] && mv $k1 $atmp || exit 1  
USRDIR="$2"
toml=$3
rnul=$( basename $k1)
#while IFS= read -r x; do  ; printf '%s\0' "$y"; done < $atmp/$rnul >> $xdata
mv $atmp/$rnul $xdata
if [ -f $USRDIR/doctrine.tsv ]; then
    sed -i 's/^POSTOP = true/POSTOP = false/' $toml
else
    echo -e "Datetime\tFile\tSize(kb)\tType\tSymlink\tChange_time\tAccessed\tOwner\tStatable" > $atmp/doctrine
    while IFS= read -r x; do
		stbool=""
		sym=""
		size_kb=0
        f="$(cut -d' ' -f3- <<< "$x")"
		filepath="$(unescf "$f")"
        dt=$(cut -d' ' -f1-2 <<< "$x")
        if [ -e "$filepath" ]; then
            mtyp=$( file --brief --mime-type "$filepath")
            if [ "$mtyp" == "application/octet-stream" ]; then mtyp="Unknown"; fi
            if [ -L "$filepath" ]; then sym="y"; fi
			read sz ctmn ae onr < <(stat --format="%s %Z %X %U" "$filepath" 2>/dev/null)
			if [ -n "$sz" ]; then
				size_kb=$(( sz / 1024 ))
		        chgtime=$(date -d "@$ctmn" +'%Y-%m-%d %H:%M:%S')
		        y=$(date -d "@$ae" +'%Y-%m-%d %H:%M:%S')
			else
				stbool="n"
				m=""
				y=""
			fi
            echo -e "$dt\t$f\t$size_kb\t$mtyp\t$sym\t$chgtime\t$y\t$onr\t$stbool" >> $atmp/doctrine
        fi
    done < $xdata
    unset IFS
    head -1 $atmp/doctrine > $USRDIR/doctrine.tsv
    tail -n +2 $atmp/doctrine | sort -t$'\t' -k8,8 -k3,3n >> $USRDIR/doctrine.tsv
    green "File doctrine.tsv created in $USRDIR"
fi
rm -rf $atmp
