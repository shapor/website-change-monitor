#!/bin/bash

STORAGE_DIR=/tmp/site-monitor

url="$1"
url_id="$(md5sum <<<$url)"

old=$STORAGE_DIR/$url_id
current="$old.$(date +%s)"

mkdir -p $STORAGE_DIR
curl "$url" >$current 2>/dev/null

[[ ! -e $old ]] && mv $current $old && exit

diff $old $current >$old.diff && rm $old.diff && exit

<$old.diff mail -s "Website Change Detected: $url" $RECIPIENT_EMAIL && rm $old.diff
