#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

# This is a basic complex plane plot
import cmath, math, pygame, os, time, colorsys, sys, random
from pygame.locals import *
import pygame.draw, pygame.image
import numpy as N

class Window:
    def __init__(self, screen_size):
        pygame.init()
        self.screen = pygame.display.set_mode(screen_size)
        self.font = pygame.font.SysFont(u'dejavusansmono', 18)
        self.screen_size = screen_size
        self.set_view(center = 0j, radius = 1.5)

    def fill(self, color = [0]*3):
        self.screen.fill(color)

    def draw_msg(self, msg, coord = (5, 5), color = (180, 180, 255)):
        text = self.font.render(msg, True, color)
        self.screen.blit(text, coord)

    def draw_line(self, start_coord, end_coord, color = (28,28,28)):
        pygame.draw.line(self.screen, color, start_coord, end_coord)

    def draw_point(self, coord, color = [242]*3):
        self.screen.set_at(coord, color)

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

class ComplexPlane(Window):
    def set_view(self, center = None, radius = None):
        if center is not None:
            self.center = center
        if radius is not None:
            self.radius = radius
        plane_min = (self.center.real - self.radius, self.center.imag - self.radius)
        plane_max = (self.center.real + self.radius, self.center.imag + self.radius)
        # Coordinate conversion vector
        self.offset = (plane_min[0], plane_min[1])
        self.scale = (
            self.screen_size[0] / float(plane_max[0] - plane_min[0]),
            self.screen_size[1] / float(plane_max[1] - plane_min[1])
        )

    def convert_to_plane(self, screen_coord):
        return complex(
            screen_coord[0] / self.scale[0] + self.offset[0],
            ((self.screen_size[1] - screen_coord[1]) / self.scale[1] + self.offset[1])
        )

    def convert_to_screen(self, plane_coord):
        return (
            int((plane_coord.real - self.offset[0]) * self.scale[0]),
            self.screen_size[1] - int((plane_coord.imag - self.offset[1]) * self.scale[1])
        )

    def draw_complex(self, complex_coord, color = [242]*3):
        self.draw_point(self.convert_to_screen(complex_coord), color)

    def draw_axis(self, axis_color=(28,28,28)):
        center_coord = self.convert_to_screen(0j)
        self.draw_line(
            (center_coord[0], 0),
            (center_coord[0], self.screen_size[1]),
            color = axis_color)
        self.draw_line(
            (0, center_coord[1]),
            (self.screen_size[0], center_coord[1]),
            color = axis_color)

def rotate_point(point, angle):
    return complex(point[0] * math.cos(angle) - point[1] * math.sin(angle),
                   point[0] * math.sin(angle) + point[1] * math.cos(angle))

class Path:
    def __init__(self, points):
        self.points = points
        self.xpath = N.array(map(lambda x: x.__getattribute__("real"), self.points))
        self.ypath = N.array(map(lambda x: x.__getattribute__("imag"), self.points))

    def points_pairs(self):
        for idx in xrange(len(self.points) - 1):
            yield (self.points[idx], self.points[idx + 1])

    def lines(self, size):
        for a, b in self.points_pairs():
            for point in N.linspace(a, b, size):
                yield(point)

    def sin(self, size, factor = 0.23, cycles = 1, direction="left"):
        for a, b in self.points_pairs():
            idx = 0
            angle = cmath.phase(b - a)
            distance = cmath.polar(b - a)[0]
            sinx = N.linspace(0, distance, size)
            if direction == "left" or (angle >= -0.5 * math.pi and angle <= 0.5 * math.pi):
                sign = 1
            else:
                sign = -1
            siny = map(lambda x: sign * math.sin(cycles * x * math.pi / float(distance)), sinx)
            for idx in xrange(size):
                p = (sinx[idx], siny[idx] * factor)
                yield a + rotate_point(p, angle)

    def splines(self, size):
        import scipy.interpolate
        t = N.arange(self.xpath.shape[0], dtype=float)
        t /= t[-1]
        nt = N.linspace(0, 1, size)
        x1 = scipy.interpolate.spline(t, self.xpath, nt)
        y1 = scipy.interpolate.spline(t, self.ypath, nt)
        for pos in xrange(len(nt)):
            yield complex(x1[pos], y1[pos])


def main(argv):
    WINSIZE = (600, 600)
    plane = ComplexPlane(WINSIZE)

    src_path = N.array((0j, -1j, 0j, 1j, 0j, -1-1j))
    final_path = N.array((-1-1j, -1+1j, 1+1j, 0, 0.5-1j, 1-0.5j))
    current_path = N.copy(src_path)
    clock = pygame.time.Clock()
    frame = 0
    while True:
        plane.fill()
        plane.draw_axis()


        path = Path(current_path)
        current_path += (final_path - current_path) / 24.0
        if (frame+1) % 100 == 0:
            t = final_path
            final_path = src_path
            src_path = t
            current_path = src_path

        for point in path.lines(23):
            plane.draw_complex(point)

        for point in path.sin(42, 0.2 * math.cos(frame / 7.0), 7 * (abs(math.sin(frame / 60.0)))):
            plane.draw_complex(point, color=(42,120,23))

        for point in path.splines(500):
            plane.draw_complex(point, color=(120,10,50))

        pygame.display.update()
        for e in pygame.event.get():
            if e.type == KEYDOWN and e.key == K_ESCAPE:
                exit(0)

        frame += 1
        clock.tick(12)

if __name__ == "__main__":
    main(sys.argv)
