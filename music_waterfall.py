#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

# This is a basic Julia set explorer
import math, pygame, os, time, colorsys, sys, random
from pygame.locals import *
import pygame.draw, pygame.image
import scipy.io.wavfile
import scipy.fftpack
from utils import *

#constants
WINSIZE = map(lambda x: x*SIZE, [ 200,  200])
CENTER  = map(lambda x: x/2, WINSIZE)

FPS = 25

class AudioGraph:
    def __init__(self, window_size, frame_size, **arg):
        self.window = Window(window_size)
        self.window_size = window_size
        self.frame_size = frame_size
        self.init(**arg)

MAX_SHORT=float((2 ** (2 * 8)) / 2)
class WavGraph(AudioGraph):
    def init(self):
        self.wav_step = self.frame_size / self.window_size[1]
        self.x_range = self.window_size[0] / 2

    def render(self, buf):
        # Wav graph
        self.window.fill((0, 13, 23))
        for y in xrange(0, self.window_size[1]):
            mbuf = np.mean(buf[y * self.wav_step:(y + 1) * self.wav_step], axis=1)
            left = mbuf[0]
            right = mbuf[1]
            mono = np.mean(mbuf)
            for point, offset, color in ((left, -self.x_range / 2, (128, 0, 0)), (right, self.x_range / 2, (0, 128, 0)), (mono, 0, (0, 0, 128))):
                self.window.draw_point((int(self.x_range + offset + self.x_range * point / MAX_SHORT), y), color)

class Waterfall(AudioGraph):
    def init(self):
        self.xpos = 0

    def render(self, sg):
        if self.xpos == self.window_size[0]:
            self.xpos = 0

        sp = sg.freq

        for y in xrange(self.window_size[1], 0, -1):
            point = sp[self.window_size[1] - y]
            try:
                hue = 0.6 - 0.4 * point
                color = map(lambda x: x*255, colorsys.hsv_to_rgb(hue, 0.7, 0.7))
                self.window.draw_point((self.xpos, y), color)
                self.window.draw_point((self.xpos + 1, y), [200]*3)
            except:
                print "Error:", point, color
                #raise

        self.xpos += 1


class ModGraph(AudioGraph):
    def init(self):
        self.xpos = 0
        self.y_range = self.window_size[1] / 2.0

    def render(self, sg, info):
        if self.xpos == self.window_size[0]:
            self.xpos = 0

        freqs = [
            ((0, 40), 5., (180, 0, 0)),
            ((40, 110), 5., (80, 0, 80)),
            ((110, 236), 10., (180, 180, 0)),
            ((236, 303), 10., (0, 180, 180)),
            ((303, -1), 10., (0, 0, 180)),
        ]
        y_split = self.window_size[1] / len(freqs)
        pos = 0
        # Clean
        for y in xrange(0, self.window_size[1]):
            if y % y_split == 0:
                color = [255] * 3
            else:
                color = [0] * 3
            self.window.draw_point((self.xpos, y), color)
            self.window.draw_point((self.xpos + 1, y), [200]*3)
        # Draw
        for point, decay, color in freqs:
            val = sg.get(point, decay)
            self.window.draw_point((self.xpos, int(
                (pos+1) * y_split - y_split * val
            )), color)
            info.draw_msg("%d-%d" % (point[0], point[1]), (5, 25 + 20 * pos), color)
            pos += 1

        self.xpos += 1

def main(argv):
    if len(argv) < 2:
        print "usage: %s audio.wav [start_frame]" % argv[0]
        return

    t0 = time.time()
    freq, wav = scipy.io.wavfile.read(argv[1])
    wav_left  = wav.take(0, axis=1)
    wav_right = wav.take(1, axis=1)
    audio_frame_size = freq / FPS

    audio_frames = np.linspace(0, len(wav), int(len(wav) / freq * FPS), endpoint=False)

    pygame.mixer.init(frequency = freq, channels = len(wav[0]), buffer = audio_frame_size)

    pygame.init()
    clock = pygame.time.Clock()
    screen = Screen(WINSIZE)
    spectrogram = SpectroGram(audio_frame_size)

    waterfall = Waterfall((WINSIZE[0] * 3 / 4, int(WINSIZE[1] * 2 / 3.)), audio_frame_size)
    wavgraph = WavGraph((WINSIZE[0] / 4, int(WINSIZE[1] * 2 / 3.)), audio_frame_size)
    audiomod = ModGraph((WINSIZE[0] * 3 / 4, int(WINSIZE[1] / 3.)), audio_frame_size)
    info = Window((WINSIZE[0] / 4, WINSIZE[1] / 3))

    screen.add(waterfall.window, (0, 0))
    screen.add(wavgraph.window, (WINSIZE[0] * 3/4, 0))
    screen.add(audiomod.window, (0, WINSIZE[1] * 2/3))
    screen.add(info, (WINSIZE[0] * 3/4, WINSIZE[1] * 2/3))

    frame = 0
    if len(argv) == 3:
        frame = int(argv[2])
    sound = pygame.mixer.Sound(array = wav[audio_frames[frame]:])
    sound.play()
    while True:
        start_time = time.time()
        info.fill()
        info.draw_msg("[%04d]" % frame)
        audio_buf = wav[audio_frames[frame]:audio_frames[frame]+audio_frame_size]

        spectrogram.transform(audio_buf)

        # Waterfall
        wavgraph.render(audio_buf)
        waterfall.render(spectrogram)
        audiomod.render(spectrogram, info)


        screen.update()
        for e in pygame.event.get():
            if e.type not in (KEYDOWN, MOUSEBUTTONDOWN):
                continue
            if e.type == MOUSEBUTTONDOWN:
                print "Clicked", e.pos
            else:
                if e.key == K_ESCAPE:
                    exit(0)
        end_time = time.time()
        elapsed = end_time - start_time
        if elapsed > 1 / (FPS * 1.2):
            print "Getting slow... %s" % elapsed
        clock.tick(FPS)
        frame += 1

if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        pass
