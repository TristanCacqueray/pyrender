#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

import argparse, cmath, math, os, time, colorsys, sys, random, signal
import subprocess, multiprocessing
import pygame
from pygame.locals import *
import pygame.draw, pygame.image
import numpy as np
import scipy.io.wavfile

# for headless rendering
# export SDL_VIDEODRIVER=dummy
# export SDL_AUDIODRIVER=dummy


# Default window size constant
SIZE=7
if "FAST_RENDER" in os.environ:
    SIZE=float(os.environ["FAST_RENDER"])
WINSIZE = map(lambda x: int(x*SIZE), [ 100,  100])
CENTER  = map(lambda x: x/2, WINSIZE)
NUM_CPU=multiprocessing.cpu_count()


# Raw color
def rgb(r, g, b):
    return int(b * 0xff) | int((g * 0xff)) << 8 | int(r * 0xff) << 16

def hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(b * 0xff) | int((g * 0xff)) << 8 | int(r * 0xff) << 16

def grayscale(r):
    return int(r * 0xff) | int((r * 0xff)) << 8 | int(r * 0xff) << 16

def dark_color_factory(scale):
    def dark_color(x):
        if x == scale:
            return 0
        return hsv(0.6 + 0.4 * x / (2 * scale), 0.7, 0.5)
    return dark_color

def bright_color_factory(scale):
    def bright_color(x):
        if x == scale:
            return 0
        return hsv(0.4 + x / (6/10. * scale), 0.7, 0.7)
    return bright_color

def grayscale_color_factory(scale):
    def grayscale_color(x):
        if x == scale:
            return 0
        return grayscale(x / scale)
    return grayscale_color


# Basic maths
MAX_SHORT=float((2 ** (2 * 8)) / 2)
PHI=(1+math.sqrt(5))/2.0
def rotate_point(point, angle):
    return complex(point[0] * math.cos(angle) - point[1] * math.sin(angle),
                   point[0] * math.sin(angle) + point[1] * math.cos(angle))

def complex_fractal(param):
    window_size, offset, scale, max_iter, c, step_size, chunk = param
    # Return numpy array of window pixel (step_size length, chunk position)

    escape_limit = 1e150

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

# Multiprocessing abstraction
pool = multiprocessing.Pool(NUM_CPU, lambda : signal.signal(signal.SIGINT, signal.SIG_IGN))
def compute(method, params):
    if pool:
        params[-1] /= NUM_CPU
        params = map(lambda x: params + [x], range(NUM_CPU))
        # Compute
        res = pool.map(method, params)
        # Return flatten array
        return np.array(res).flatten()
    return method(params + [0])


# scipyio abstraction
def load_wav(wav_file, fps = 25, init_mixer = True):
    freq, wav = scipy.io.wavfile.read(wav_file)
    if freq % fps != 0:
        raise RuntimeError("Can't load wav %d Hz at %d fps" % (freq, fps))
    audio_frame_size = freq / fps
    audio_frames_path = np.linspace(0, len(wav), int(len(wav) / freq * fps), endpoint=False)
    if init_mixer:
        pygame.mixer.init(frequency = freq, channels = len(wav[0]), buffer = audio_frame_size)
    return wav, audio_frame_size, audio_frames_path


# Fft abstraction (frame based short fft)
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
        if (mono == 0).all():
            self.freq = autopower[:self.frame_size/2]
        else:
            dbres = 20*np.log10(autopower[:self.frame_size/2])
            clipres = np.clip(dbres, -40, 200) * 1 / 196.
            self.freq = clipres + 0.204081632654

# IIR filter abstraction (old way to extract low freq from audio file)
class Filter:
    def __init__(self, bpass, bstop, ftype='butter'):
        import scipy.signal.filter_design as fd
        import scipy.signal.signaltools as st
        self.b, self.a = fd.iirdesign(bpass, bstop, 1, 100, ftype=ftype, output='ba')
        self.ic = st.lfiltic(self.b, self.a, (0.0,))
    def filter(self, data):
        import scipy.signal.signaltools as st
        res = st.lfilter(self.b, self.a, data, zi=self.ic)
        self.ic = res[-1]
        return res[0]

class AudioMod:
    def __init__(self, filename, frames, filter_type, delay = 10.0):
        self.frames = frames
        self.mod = np.zeros(frames)
        self.cache_filename = "%s.mod" % filename
        if not os.path.isfile(self.cache_filename):
            if filter_type == 1:
                self.fp = Filter(0.01, 0.1, ftype='ellip')
            elif filter_type == 2:
                self.fp = Filter((0.1, 0.2),  (0.05, 0.25), ftype='ellip')
            if not os.path.isfile(filename):
                print "Could not load %s" % filename
                return
            wave_values = self.load_wave(filename)
            open(self.cache_filename, "w").write("\n".join(map(str, wave_values))+"\n")
        else:
            wave_values = map(float, open(self.cache_filename).readlines())
        imp = 0.0
        for i in xrange(0, self.frames):
            if wave_values[i] >= imp:
                imp = wave_values[i]
            else:
                delta = (imp - wave_values[i]) / delay
                imp -= delta
            self.mod[i] = imp

    def load_wave(self, filename):
        import wave
        wav = wave.open(filename, "r")
        if wav.getsampwidth() != 2 or wav.getnchannels() != 1:
            print "Only support mono 16bit encoding..."
            exit(1)

        # Read all frames
        buf = wav.readframes(wav.getnframes())

        # Convert to float array [-1; 1]
        w = np.fromstring(buf, np.int16) / float((2 ** (2 * 8)) / 2)

        step = wav.getnframes() / self.frames + 1
        wave_values = []
        for i in xrange(0, wav.getnframes(), step):
            wf = w[i:i+step]
            if self.fp:
                wf = self.fp.filter(wf)

            v = np.max(np.abs(wf))
            wave_values.append(float(v))
        return wave_values

    def plot(self):
        p = subprocess.Popen(['gnuplot'], stdin=subprocess.PIPE)
        open("/tmp/plot", "w").write("\n".join(map(lambda x: str(self.get(x)), range(0, self.frames))))
        #for i in xrange(0, self.frames):

        p.stdin.write("plot '/tmp/plot' with lines\n")
        p.wait()

    def get(self, frame):
        return self.mod[frame]



# Pygame abstraction
class Screen:
    def __init__(self, screen_size):
        pygame.init()
        self.font = pygame.font.SysFont(u'dejavusansmono', 18)
        self.screen = pygame.display.set_mode(screen_size)
        self.windows = []

    def draw_msg(self, msg, coord = (5, 5), color = (180, 180, 255)):
        text = self.font.render(msg, True, color)
        self.screen.blit(text, coord)

    def capture(self, dname, frame):
        if not os.path.isdir(dname):
            os.mkdir(dname)
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
            if window.pixels is not None:
                pygame.surfarray.blit_array(window.surface, window.pixels)
            self.screen.blit(window.surface, coord)

class ScreenPart:
    def __init__(self, window_size):
        try:
            self.surface = pygame.Surface(window_size)
            self.window_size = map(int, window_size)
            self.length = self.window_size[0] * self.window_size[1]
            self.pixels = np.zeros(self.length, dtype='i4').reshape(*self.window_size)
        except:
            print "Invalid window_size", window_size
            raise

    def blit(self, nparray):
        pygame.surfarray.blit_array(self.surface, nparray.reshape(*self.window_size))

# Ready to use 'widget'
class WavGraph(ScreenPart):
    def __init__(self, window_size, frame_size):
        ScreenPart.__init__(self, window_size)
        self.frame_size = frame_size
        self.wav_step = self.frame_size / self.window_size[1]
        self.x_range = self.window_size[0] / 2

    def render(self, buf):
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

class Waterfall(ScreenPart):
    def __init__(self, window_size, frame_size, width = 1):
        ScreenPart.__init__(self, window_size)
        self.frame_size = frame_size
        self.width = width

    def render(self, spectrogram):
        self.pixels = np.roll(self.pixels, -1, axis=0)
        for y in xrange(self.window_size[1] - 1, 0, -1):
            inv_y = self.window_size[1] - y
            if self.width == 1:
                point = spectrogram.freq[inv_y]
            else:
                if (inv_y + 1) * self.width >= len(spectrogram.freq):
                    break
                point = np.mean(spectrogram.freq[int(inv_y * self.width):int((inv_y + 1) * self.width)])
            self.pixels[-1][y] = hsv(0.5 + 0.3 * point, 0.3 + 0.6 * point, 0.2 + 0.8 * point)


# Legacy abstraction
class Window:
    def __init__(self, window_size):
        self.surface = pygame.Surface(window_size)
        self.font = pygame.font.SysFont(u'dejavusansmono', 18)
        self.window_size = window_size
        self.length = window_size[0] * window_size[1]
        self.pixels = None

    def fill(self, color = [0]*3):
        self.surface.fill(color)

    def draw_msg(self, msg, coord = (5, 5), color = (180, 180, 255)):
        text = self.font.render(msg, True, color)
        self.surface.blit(text, coord)

    def draw_line(self, start_coord, end_coord, color = (28,28,28)):
        pygame.draw.line(self.surface, color, start_coord, end_coord)

    def draw_point(self, coord, color = [242]*3):
        self.surface.set_at(coord, color)

    def blit(self, nparray):
        pygame.surfarray.blit_array(self.surface, nparray.reshape(*self.window_size))

class ComplexPlane:
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

    def convert_to_plane(self, screen_coord):
        return complex(
            screen_coord[0] / self.scale[0] + self.offset[0],
            ((self.window_size[1] - screen_coord[1]) / self.scale[1] + self.offset[1])
        )

    def convert_to_screen(self, plane_coord):
        return [
            int((plane_coord.real - self.offset[0]) * self.scale[0]),
            self.window_size[1] - int((plane_coord.imag - self.offset[1]) * self.scale[1])
        ]

    def draw_complex(self, complex_coord, color = [242]*3):
        self.draw_point(self.convert_to_screen(complex_coord), color)

    def draw_axis(self, axis_color=(28,28,28)):
        center_coord = self.convert_to_screen(0j)
        self.draw_line(
            (center_coord[0], 0),
            (center_coord[0], self.window_size[1]),
            color = axis_color)
        self.draw_line(
            (0, center_coord[1]),
            (self.window_size[0], center_coord[1]),
            color = axis_color)

# Modulation
class Path:
    def __init__(self, points, size):
        self.points = points
        self.size = size
        self.len_pairs = float(len(points) - 1)
        self.xpath = np.array(map(lambda x: x.__getattribute__("real"), self.points))
        self.ypath = np.array(map(lambda x: x.__getattribute__("imag"), self.points))

    def points_pairs(self):
        for idx in xrange(len(self.points) - 1):
            yield (self.points[idx], self.points[idx + 1])

    def lines(self):
        path = []
        for a, b in self.points_pairs():
            for point in np.linspace(a, b, self.size / self.len_pairs):
                path.append(point)
        return path

    def gen_lines(self):
        path = self.lines()
        for c in path: yield c

    def sin(self, factor = 0.23, cycles = 1, sign = 1, maxy = 1.0):
        path = []
        for a, b in self.points_pairs():
            idx = 0
            angle = cmath.phase(b - a)
            distance = cmath.polar(b - a)[0]
            sinx = np.linspace(0, distance, self.size / self.len_pairs)
            siny = map(lambda x: sign * maxy * math.sin(cycles * x * math.pi / float(distance)), sinx)
            for idx in xrange(int(self.size / self.len_pairs)):
                p = (sinx[idx], siny[idx] * factor)
                path.append(a + rotate_point(p, angle))
        return path

    def gen_sin(self, factor = 0.23, cycles = 1, sign = 1, maxy = 1.0):
        path = self.sin(factor, cycles, sign, maxy)
        for c in path: yield c

    def splines(self):
        import scipy.interpolate
        path = []
        t = np.arange(self.xpath.shape[0], dtype=float)
        t /= t[-1]
        nt = np.linspace(0, 1, self.size)
        x1 = scipy.interpolate.spline(t, self.xpath, nt)
        y1 = scipy.interpolate.spline(t, self.ypath, nt)
        for pos in xrange(len(nt)):
            path.append(complex(x1[pos], y1[pos]))
        return path

    def gen_splines(self):
        path = self.splines()
        for c in path: yield c


def main(argv):
    WINSIZE = (600, 600)
    screen = Screen(WINSIZE)
    plane = ComplexPlane(WINSIZE)
    screen.add(plane)

    src_path = np.array((0j, -1j, 0j, 1j, 0j, -1-1j))
    final_path = np.array((-1-1j, -1+1j, 1+1j, 0, 0.5-1j, 1-0.5j))
    current_path = np.copy(src_path)
    clock = pygame.time.Clock()
    frame = 0
    while True:
        plane.fill()
        plane.draw_axis()

        path = Path(current_path, 600)
        current_path += (final_path - current_path) / 24.0
        if (frame+1) % 100 == 0:
            t = final_path
            final_path = src_path
            src_path = t
            current_path = src_path

        for point in path.gen_lines():
            plane.draw_complex(point)

        for point in path.gen_sin(0.2 * math.cos(frame / 7.0), 7 * (abs(math.sin(frame / 60.0)))):
            plane.draw_complex(point, color=(42,120,23))

        for point in path.gen_splines():
            plane.draw_complex(point, color=(120,10,50))

        screen.update()
        pygame.display.update()

        for e in pygame.event.get():
            if e.type == KEYDOWN and e.key == K_ESCAPE:
                exit(0)

        frame += 1
        clock.tick(12)

if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        raise
        pass
