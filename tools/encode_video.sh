#!/bin/bash

set -ex
[ -f "${WAV}" ] || exit -1
[ -d "${RECORD_DIR}" ] || exit -1

O=$(basename ${RECORD_DIR})

START_FRAME=${1:-0}

ffmpeg  -y -framerate 24  -start_number ${START_FRAME} -i "${RECORD_DIR}/%04d.png" -i ${WAV} -c:v libvpx -threads 4 -b:v 5M -c:a libvorbis \
    /tmp/${O}.webm


mplayer -zoom -fs /tmp/${O}.webm
