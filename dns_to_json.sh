#!/bin/bash
recordtype="MX"
domain="google.com"
digjson=$( dig $recordtype $domain +nocomments +noquestion +noauthority +noadditional +nostats|
    awk '{if (NR>3){print}}' |
    tr -s '\t' |
    jq -R 'split("\t") |{name:.[0],ttl:.[1],class:.[2],type:.[3],value:.[4]}'|
    jq --slurp .
)
echo $digjson >> $domain.json

