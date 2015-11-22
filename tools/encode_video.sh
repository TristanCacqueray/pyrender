#!/bin/bash

set -ex
[ -f "${WAV}" ] || exit -1
[ -d "${RECORD_DIR}" ] || exit -1

O=$(basename ${RECORD_DIR})

ffmpeg  -y -framerate 24 -i "${RECORD_DIR}/%04d.png" -i ${WAV} -c:v libvpx -threads 4 -b:v 5M -c:a libvorbis \
    /tmp/${O}.webm

mplayer -zoom -ss $[ $1 / 24 ] -fs /tmp/${O}.webm
