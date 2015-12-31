#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

import argparse
import cmath, math, pygame, os, time, colorsys, sys, random
from pygame.locals import *
import pygame.draw, pygame.image
import numpy as np
import subprocess, multiprocessing
import scipy.io.wavfile

# for headless rendering
# export SDL_VIDEODRIVER=dummy
# export SDL_AUDIODRIVER=dummy

#constants
SIZE=7
if "FAST_RENDER" in os.environ:
    SIZE=float(os.environ["FAST_RENDER"])
WINSIZE = map(lambda x: int(x*SIZE), [ 100,  100])
WAV_WIDTH = int(WINSIZE[0] / 5)
MOD_WIDTH = int(WINSIZE[0] / 5)
SG_HEIGHT = int(WINSIZE[1] / 5)

NUM_CPU=multiprocessing.cpu_count()

MAX_SHORT=float((2 ** (2 * 8)) / 2)
PHI = (1+math.sqrt(5))/2.0

class Screen:
    def __init__(self, screen_size):
        pygame.init()
        self.screen = pygame.display.set_mode(screen_size)
        self.windows = []

    def capture(self, frame):
        dname = os.environ['RECORD_DIR']
        try:
            os.mkdir(dname)
        except:
            pass
        fname = "%s/%04d.png" % (dname, frame)
        try:
            pygame.image.save(self.screen, fname)
        except Exception, e:
            print fname, e
            raise

    def add(self, window, coord = (0, 0)):
        self.windows.append((window, coord))

    def update(self):
        for window, coord in self.windows:
            pygame.surfarray.blit_array(window.surface, window.pixels)
            self.screen.blit(window.surface, coord)
        pygame.display.update()

# Audio mod generator
class SpectroGram:
    def __init__(self, frame_size):
        self.frame_size = frame_size
        overlap_fac = 0.5
        self.hop_size = np.int32(np.floor(self.frame_size * (1 - overlap_fac)))
        self.fft_window = np.hanning(self.frame_size)
        self.inner_pad = np.zeros(self.frame_size)
        self.amps = {}

    def transform(self, buf):
        self.buf = buf
        mono = np.mean(buf, axis=1)
        windowed = self.fft_window * mono
        padded = np.append(windowed, self.inner_pad)
        spectrum = np.fft.fft(padded) / self.frame_size
        autopower = np.abs(spectrum * np.conj(spectrum))
        dbres = 20*np.log10(autopower[:self.frame_size/2])
        clipres = np.clip(dbres, -40, 200) * 1 / 196.
        self.freq = clipres

    def get(self, freq_range, decay = 10.):
        if freq_range not in self.amps:
            self.amps[freq_range] = 0
        vals = self.freq[freq_range[0]:freq_range[1]]
        if freq_range[1] - freq_range[0] > 25:
            val = np.max(vals)
        else:
            val = np.mean(vals)
        val = max(0, val)
        if val > self.amps[freq_range]:
            self.amps[freq_range] = val
        else:
            self.amps[freq_range] -= (self.amps[freq_range] - val) / decay
        return self.amps[freq_range]

def rgb(r, g, b):
    return int(b * 0xff) | int((g * 0xff)) << 8 | int(r * 0xff) << 16

def hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(b * 0xff) | int((g * 0xff)) << 8 | int(r * 0xff) << 16

def compute_fractal(param):
    window_size, offset, scale, c, step_size, chunk = param

    max_iter = 42.
    escape_limit = 10000

    results = np.zeros(step_size, dtype='i4')
    #return results
    pos = 0

    while pos < step_size:
        step_pos = pos + chunk * step_size
        screen_coord = (step_pos / window_size[1], step_pos % window_size[1])
        z = complex(
            screen_coord[0] / scale[0] + offset[0],
            ((window_size[1] - screen_coord[1]) / scale[1] + offset[1])
        )
        if c is None:
            # Mandelbrot set
            u = 0
        else:
            # Julia set
            u = z
            z = c
        idx = 0
        while idx < max_iter:
            u = u * u + z
            if abs(u.real) > escape_limit or abs(u.imag) > escape_limit:
                break
            idx += 1
        results[pos] = idx
        pos += 1
    return results

def vector_color(x):
    if x == 42:
        return 0
    return hsv(0.6 + 0.4 * x / (2 * 42.), 0.7, 0.5)

class Scene:
    def __init__(self, window_size):
        try:
            print window_size
            self.surface = pygame.Surface(window_size)
        except:
            print "Invalid window_size", window_size
            raise
        self.window_size = window_size
        self.length = window_size[0] * window_size[1]
        self.pixels = np.zeros(self.length).reshape(*self.window_size)

class Fractal(Scene):
    def __init__(self, window_size, c = None):
        Scene.__init__(self, window_size)
        self.c = c
        self.set_view(0j, 1)
        self.color_vector = np.vectorize(vector_color)
        self.last_view = None

    def set_view(self, center = None, radius = None):
        if center is not None:
            self.center = center
        if radius is not None:
            if radius == 0:
                raise RuntimeError("Radius can't be null")
            self.radius = radius
        plane_min = (self.center.real - self.radius, self.center.imag - self.radius)
        plane_max = (self.center.real + self.radius, self.center.imag + self.radius)
        # Coordinate conversion vector
        self.offset = (plane_min[0], plane_min[1])
        self.scale = (
            self.window_size[0] / float(plane_max[0] - plane_min[0]),
            self.window_size[1] / float(plane_max[1] - plane_min[1])
        )

    def draw_complex(self, plane_coord, color = 0xffffff):
        coord = (int((plane_coord.real - self.offset[0]) * self.scale[0]),
                        self.window_size[1] - int((plane_coord.imag - self.offset[1]) * self.scale[1]))
        if coord[1] >= self.pixels.shape[1] or coord[0] >= self.pixels.shape[0]:
            return
        self.pixels[coord[0]][coord[1]] = color

    def render(self, pool = None):
        if self.c is None:
            if (self.center, self.radius) == self.last_view:
                # Reuse pre-render
                self.pixels = self.pixels_copy.copy()
                return
            self.last_view = (self.center, self.radius)
        base_param = [self.window_size, self.offset, self.scale, self.c]
        if pool:
            base_param.append(self.length / NUM_CPU)
            params = map(lambda x: base_param + [x], range(NUM_CPU))
            nparray = np.array(pool.map_async(compute_fractal, params).get(10000)).flatten()
        else:
            params = base_param + [self.length, 0]
            nparray = compute_fractal(params)
        nparray = self.color_vector(nparray)
        self.pixels = nparray.reshape(*self.window_size)
        if self.c is None: # Keep mandelbrot render
            self.pixels_copy = self.pixels.copy()


class WavGraph(Scene):
    def __init__(self, window_size, frame_size):
        Scene.__init__(self, window_size)
        self.frame_size = frame_size
        self.wav_step = self.frame_size / self.window_size[1]
        self.x_range = self.window_size[0] / 2

    def render(self, spectrogram):
        buf = spectrogram.buf
        # Wav graph
        pixels = np.zeros(self.length, dtype='i4').reshape(*self.window_size)
        for y in xrange(0, self.window_size[1]):
            mbuf = np.mean(buf[y * self.wav_step:(y + 1) * self.wav_step], axis=1)
            left = mbuf[0]
            right = mbuf[1]
            mono = np.mean(mbuf)
            for point, offset, color in ((left, -self.x_range / 2, 0xf10000), (right, self.x_range / 2, 0x00f100), (mono, 0, 0xf1)):
                pixels[int(self.x_range + offset + (self.x_range / 2.) * point / MAX_SHORT)][y] = color
        self.pixels = pixels


class Waterfall(Scene):
    def __init__(self, window_size, frame_size):
        Scene.__init__(self, window_size)
        self.frame_size = frame_size
        self.pixels = np.zeros(self.length, dtype='i4').reshape(*self.window_size)

    def render(self, spectrogram):
        self.pixels = np.roll(self.pixels, -1, axis=0)
        for y in xrange(self.window_size[1] - 1, 0, -1):
            inv_y = self.window_size[1] - y
            point = np.mean(spectrogram.freq[inv_y * 3:(inv_y + 2) * 3])
            #point = spectrogram.freq[inv_y]
            self.pixels[-1][y] = hsv(0.6 - 0.4 * point, 0.7, 0.7)

class Modulator(Scene):
    def __init__(self, window_size, bpm, fps):
        Scene.__init__(self, window_size)
        self.pixels = np.zeros(self.length, dtype='i4').reshape(*self.window_size)
        self.freqs = [
            [0., (250, 403), 4., 0x008080],
            [0., (180, 230), 10., 0x808080],
            [0., (95, 127), 10., 0x808000],
            [0., (0, 3), 5., 0xff0000],
        ]
        self.scale = fps * 4 * 60 / bpm

    def update(self, frame, spectrogram, scene, debug):
        # Update mods
        for freq in self.freqs:
            current, freq_range, decay, color = freq
            vals = spectrogram.freq[freq_range[0]:freq_range[1]]
            if freq_range[1] - freq_range[0] > 25:
                val = np.max(vals)
            else:
                val = np.mean(vals)
            val = max(0, val)
            if val > current:
                freq[0] = val
            else:
                freq[0] -= (current - val) / decay

        # Update scene
        if frame >= 0:    # Intro
            scene_start, scene_len = 0, 228.
            if frame == scene_start:
                debug.set_view(center = (-0.1 + 1j), radius = 0.12)
                scene.set_view(center = 0j, radius = 3.0)
                scene.c = -0.1 + 1.1j
                self.c_path = np.linspace(scene.c, -0.1 + 0.9j, scene_len)
            #mod = complex(-0.01, PHI * -0.17 * lowmod.get(frame))
            #print frame
            scene.c = self.c_path[frame -scene_len] #+ mod



    def render(self):
        self.pixels = np.roll(self.pixels, -1, axis=0)
        y_split = self.window_size[1] / len(self.freqs)
        cur_pos = -1
        pos = 0
        self.pixels[cur_pos] *= 0
        for freq in self.freqs:
            if pos:
                self.pixels[cur_pos][y_split * pos] = 0x4e4e4e
            self.pixels[cur_pos][-1 + (pos + 1 ) * y_split - y_split * freq[0]] = freq[-1]
            pos += 1

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--wav", required = True)
    parser.add_argument("--play", action="store_const", const=True)
    parser.add_argument("--multiprocess", action="store_const", const=True)
    parser.add_argument("--single", action="store_const", const=True)
    parser.add_argument("--bpm", type=float, default=105.)
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--stop", type=int, default=9001)
    parser.add_argument("--debug", action="store_const", const=True)
    args = parser.parse_args()


    freq, wav = scipy.io.wavfile.read(args.wav)
    audio_frame_size = freq / args.fps
    audio_frames = np.linspace(0, len(wav), int(len(wav) / freq * args.fps), endpoint=False)
    spectrogram = SpectroGram(audio_frame_size)

    mod = Modulator((MOD_WIDTH, SG_HEIGHT), args.bpm, args.fps)
    start_frame = args.start
    end_frame = min(len(audio_frames), start_frame + args.stop)

    if args.play:
        pygame.mixer.init(frequency = freq, channels = len(wav[0]), buffer = audio_frame_size)

    screen = Screen(WINSIZE)
    waterfall = Waterfall((WINSIZE[0] - WAV_WIDTH - MOD_WIDTH, SG_HEIGHT), audio_frame_size)
    wavgraph = WavGraph((WAV_WIDTH, WINSIZE[1] - SG_HEIGHT), audio_frame_size)
    if args.debug:
        debug = Fractal((WINSIZE[0] - WAV_WIDTH, WINSIZE[1] - SG_HEIGHT))
        scene = Fractal((WAV_WIDTH, SG_HEIGHT))
        screen.add(debug)
        screen.add(scene, (WINSIZE[0] - WAV_WIDTH, WINSIZE[1] - SG_HEIGHT))
    else:
        debug = Fractal((WAV_WIDTH, SG_HEIGHT))
        scene = Fractal((WINSIZE[0] - WAV_WIDTH, WINSIZE[1] - SG_HEIGHT))
        screen.add(scene)
        screen.add(debug, (WINSIZE[0] - WAV_WIDTH, WINSIZE[1] - SG_HEIGHT))

    screen.add(waterfall, (0, WINSIZE[1] - SG_HEIGHT))
    screen.add(mod,  (WINSIZE[0] - WAV_WIDTH - MOD_WIDTH, WINSIZE[1] - SG_HEIGHT))
    screen.add(wavgraph, (WINSIZE[0] - WAV_WIDTH, 0))

    if args.multiprocess:
        pool = multiprocessing.Pool(NUM_CPU)
    else:
        pool = None

    clock = pygame.time.Clock()
    c_values = []
    frame = 0

    # Init
    debug.c = None
    while True:
        start_time = time.time()

        audio_buf = wav[audio_frames[frame]:audio_frames[frame]+audio_frame_size]
        spectrogram.transform(audio_buf)
        mod.update(frame, spectrogram, scene, debug)

        c_values.append(scene.c)
        wavgraph.render(spectrogram)
        waterfall.render(spectrogram)
        if frame >= start_frame:
            debug.render(pool)
            if not args.debug:
                scene.render()
            idx = 1
            c_num_draw = 42
            while idx < min(c_num_draw, len(c_values)):
                point = c_values[-idx]
                debug.draw_complex(point, rgb(*[1 * (c_num_draw - 1 - idx) / float(c_num_draw)] * 3))
                idx += 1
            mod.render()
            screen.update()
            if "RECORD_DIR" in os.environ:
                screen.capture(frame)

            end_time = time.time()
            #print end_time - start_time
            elapsed = end_time - start_time
            if elapsed > 1 / (args.fps * 1.2):
                print "Getting slow... %s" % elapsed
            if args.single:
                return raw_input("press enter")

        if frame == start_frame and args.play:
            sound = pygame.mixer.Sound(array = wav[audio_frames[start_frame]:])
            sound.play()

        frame += 1
        if frame >= end_frame:
            break

        for e in pygame.event.get():
            if  e.type == MOUSEBUTTONDOWN: print e.pos
            elif e.type == KEYDOWN and e.key == K_ESCAPE: exit(0)

        if frame >= start_frame:
            clock.tick(args.fps)

if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        pass
