#!/usr/bin/env bash
config_file="$1" ; option="$2" ; value="$3" ; set_to="true"
[[ ! -f $config_file ]] && echo "Error unabled to locate configfile: $config_file and update setting" && exit 1
[[ "$value" = "true" ]] && set_to="false"
zz=$(grep -Fm1 "$option =" $config_file | cut -d'=' -f2 | tr -d ' ')
if [ -n "$zz" ] && [ "$zz" != "$set_to" ]; then sed -i "s/^${option} = ${value}/${option} = ${set_to}/" $config_file ; fi
echo "config file $config_file Sucessfully updated"
