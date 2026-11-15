#!/bin/bash
config_file="$1" ; option="$2" ; value="$3" ; set_to="true"
[[ ! -f $config_file ]] && echo "Error unabled to locate configfile: $config_file and update setting" && exit 1
[[ "$value" = "true" ]] && set_to="false"
zz=$( grep -Fm 1 "export ${option}=" "$config_file" | awk -F'"' '{print $2}' )
if [ -n "$zz" ] && [ "$zz" != "$set_to" ]; then
    sed -i "s/^export ${option}=\"${value}\"/export ${option}=\"${set_to}\"/" $config_file
fi
echo "config file $config_file Sucessfully updated"

