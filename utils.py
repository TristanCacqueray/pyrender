#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

# This is a basic complex plane plot
import cmath, math, pygame, os, time, colorsys, sys, random
from pygame.locals import *
import pygame.draw, pygame.image
import numpy as N
import subprocess, multiprocessing

#constants
if "RECORD_DIR" in os.environ:
    SIZE=6
else:
    SIZE=4
if "FAST_RENDER" in os.environ:
    SIZE=2

class Screen:
    def __init__(self, screen_size):
        pygame.init()
        self.screen = pygame.display.set_mode(screen_size)

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

    def display_fullscreen(self, surface):
        self.screen.blit(surface, (0, 0))
        pygame.display.update()

    def display(self, surfaces):
        for surface, coord in surfaces:
            self.screen.blit(surface, coord)
        pygame.display.update()

class Window:
    def __init__(self, window_size):
        self.window = pygame.Surface(window_size)
        self.font = pygame.font.SysFont(u'dejavusansmono', 18)
        self.window_size = window_size

    def fill(self, color = [0]*3):
        self.window.fill(color)

    def draw_msg(self, msg, coord = (5, 5), color = (180, 180, 255)):
        text = self.font.render(msg, True, color)
        self.window.blit(text, coord)

    def draw_line(self, start_coord, end_coord, color = (28,28,28)):
        pygame.draw.line(self.window, color, start_coord, end_coord)

    def draw_point(self, coord, color = [242]*3):
        self.window.set_at(coord, color)

class ComplexPlane(Window):
    def __init__(self, window_size):
        Window.__init__(self, window_size)
        self.set_view(center = 0j, radius = 1.5)

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

def rotate_point(point, angle):
    return complex(point[0] * math.cos(angle) - point[1] * math.sin(angle),
                   point[0] * math.sin(angle) + point[1] * math.cos(angle))

class Path:
    def __init__(self, points, size):
        self.points = points
        self.size = size
        self.len_pairs = float(len(points) - 1)
        self.xpath = N.array(map(lambda x: x.__getattribute__("real"), self.points))
        self.ypath = N.array(map(lambda x: x.__getattribute__("imag"), self.points))

    def points_pairs(self):
        for idx in xrange(len(self.points) - 1):
            yield (self.points[idx], self.points[idx + 1])

    def lines(self):
        path = []
        for a, b in self.points_pairs():
            for point in N.linspace(a, b, self.size / self.len_pairs):
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
            sinx = N.linspace(0, distance, self.size / self.len_pairs)
            siny = map(lambda x: sign * maxy * math.sin(cycles * x * math.pi / float(distance)), sinx)
            for idx in xrange(int(self.size / self.len_pairs)):
                p = (sinx[idx], siny[idx] * factor)
                path.append(a + rotate_point(p, angle))
        return path

    def gen_sin(self, factor = 0.23, cycles = 1, sign = 1, maxy = 1.0):
        path = self.sin()
        for c in path: yield c

    def splines(self):
        import scipy.interpolate
        path = []
        t = N.arange(self.xpath.shape[0], dtype=float)
        t /= t[-1]
        nt = N.linspace(0, 1, self.size)
        x1 = scipy.interpolate.spline(t, self.xpath, nt)
        y1 = scipy.interpolate.spline(t, self.ypath, nt)
        for pos in xrange(len(nt)):
            path.append(complex(x1[pos], y1[pos]))
        return path

    def gen_splines(self):
        path = self.splines()
        for c in path: yield c

# Audio mod generator
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
        self.mod = N.zeros(frames)
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
        w = N.fromstring(buf, N.int16) / float((2 ** (2 * 8)) / 2)

        step = wav.getnframes() / self.frames + 1
        wave_values = []
        for i in xrange(0, wav.getnframes(), step):
            wf = w[i:i+step]
            if self.fp:
                wf = self.fp.filter(wf)

            v = N.max(N.abs(wf))
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



def main(argv):
    WINSIZE = (600, 600)
    screen = Screen(WINSIZE)
    plane = ComplexPlane(WINSIZE)

    src_path = N.array((0j, -1j, 0j, 1j, 0j, -1-1j))
    final_path = N.array((-1-1j, -1+1j, 1+1j, 0, 0.5-1j, 1-0.5j))
    current_path = N.copy(src_path)
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

        screen.display(((plane.window, (0,0)),))

        for e in pygame.event.get():
            if e.type == KEYDOWN and e.key == K_ESCAPE:
                exit(0)

        frame += 1
        clock.tick(12)

if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        pass
