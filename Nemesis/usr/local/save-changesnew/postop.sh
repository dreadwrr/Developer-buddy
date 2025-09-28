#!/bin/bash
#   Developer buddy 3.0 core                                               9/27/2025
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
while IFS= read -r x; do y="$(unescf "$x")" ; printf '%s\0' "$y"; done < $atmp/$rnul >> $xdata
if [ -f $USRDIR/doctrine.tsv ]; then
    sed -i 's/^POSTOP = true/POSTOP = false/' $toml
else
    echo -e "Datetime\tFile\tSize(kb)\tType\tModified\tAccessed\tOwner" > $atmp/doctrine
    while IFS= read -r -d '' x; do
        f="$(cut -d' ' -f3- <<< "$x")"
        dt=$(cut -d' ' -f1-2 <<< "$x")
        if [ -e "$f" ] && [ -f "$f" ]; then
            onr=$( stat -c "%U" "$f")
            mtyp=$( file --brief --mime-type "$f")
            if [ "$mtyp" == "application/octet-stream" ]; then mtyp="Unknown"; fi
            if [ -L "$f" ]; then mtyp="Symlink"; fi
            sz=$( stat -c %s "$f")
            md=$( stat -c '%Y' "$f") ; x=$(date -d "@$md" +'%Y-%m-%d %H:%M:%S')
            ae=$( stat -c '%X' "$f") ; y=$(date -d "@$ae" +'%Y-%m-%d %H:%M:%S')
            echo -e "$dt\t$f\t$(( sz / 1024 ))\t$mtyp\t$x\t$y\t$onr" >> $atmp/doctrine
        fi
    done < $xdata
    unset IFS
    head -1 $atmp/doctrine > $USRDIR/doctrine.tsv
    tail -n +2 $atmp/doctrine | sort -t$'\t' -k7,7 -k3,3n >> $USRDIR/doctrine.tsv
    green "File doctrine.tsv created in $USRDIR"
fi
rm -rf $atmp
