#!/bin/bash
TEST_FILE_PATH="$1"; shift
mirrors=($@)
TIMEOUT=5
BYTE_RANGE_START=0
BYTE_RANGE_END=5000000
BEST_SERVER=$({
	for mirror in ${mirrors[@]}; do
		curl -r $BYTE_RANGE_START-$BYTE_RANGE_END -m $TIMEOUT -s -w "%{speed_download} " -o /dev/null $mirror/$TEST_FILE_PATH
		echo -e $mirror
	done
} | awk 'BEGIN{s=0; u=""}{if ($1>0+s) {s=$1; u=$2}} END{print u}')
echo $BEST_SERVER