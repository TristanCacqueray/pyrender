#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

# This is a basic Julia set explorer
import math, pygame, os, time, colorsys, sys, random
from pygame.locals import *
import pygame.draw, pygame.image

from utils import *

#constants
WINSIZE = map(lambda x: x*SIZE, [ 100,  100])
CENTER  = map(lambda x: x/2, WINSIZE)

PHI=(1+math.sqrt(5))/2.0

class JuliaSet:
    def __init__(self, c = complex(0, 0), escape_limit=1e100, max_iter=69):
        self.c = c
        self.escape_limit = escape_limit
        self.max_iter = max_iter
        self.screen = Screen(WINSIZE)

    def render(self, plane, frame):
        start_time = time.time()
        plane.fill((0, 0, 0))
        self.draw_fractal(plane)
        plane.draw_axis()
        self.draw_function_msg(plane)
        self.draw_cpoint(plane)
        self.screen.display_fullscreen(plane.window)
        print "%04d: %.2f sec: c/center/radius = '%s' '%s' %s" % (frame, time.time() - start_time, self.c, plane.center, plane.radius)

    def draw_fractal(self, plane):
        for y in xrange(WINSIZE[1]):
            for x in xrange(WINSIZE[0]):
                z = plane.convert_to_plane((x, y))
                for i in xrange(0, self.max_iter):
                    z = z * z + self.c
                    if abs(z.real) > self.escape_limit or abs(z.imag) > self.escape_limit:
                        break
                if i + 1 == self.max_iter:
                    continue
                color = tuple([255 * i / float(self.max_iter)] * 3)
                plane.draw_point((x,y), color)

    def draw_function_msg(self, plane):
        if self.c.real >= 0: r_sign = "+"
        else:                r_sign = ""
        if self.c.imag >= 0: i_sign = "+"
        else:                i_sign = ""
        self.c_str = "z*z%s%.5f%s%.5fj" % (r_sign, self.c.real, i_sign, self.c.imag)
        plane.draw_msg(self.c_str)

    def draw_cpoint(self, plane):
        plane.draw_complex(self.c, (255, 0, 0))

seeds = (
    complex(PHI, PHI),
    (-0.15000+0.95000j),
    (-0.64000+0.70000j),
    (-0.64000+0.50000j),
    (+0.47000-0.24000j),
    (-0.77000-0.15000j),
    (-1.38000-0.09000j),
    (-1.17000+0.18000j),
    (-0.08000+0.70000j),
    (-0.11000+1.00000j),
    (0.28200+0.48000j),
)


def main(argv):
    if len(argv) == 1:
        print "JuliaSet explorer"
        print "================="
        print ""
        print "Click the window to center"
        print "Use keyboard arrow to move window, 'a'/'e' to zoom in/out, 'r' to reset view"
        print "Use 'qzsd' to change c value or RETURN key to browse known seeds"

    pygame.init()
    clock = pygame.time.Clock()
    plane = ComplexPlane(WINSIZE)
    c = random.choice(seeds)
    # Usage allow reuse of frame definition (c, plane center, radius)
    if len(argv) >= 2: c = complex(argv[1])
    if len(argv) >= 3: plane.set_view(center = complex(argv[2]))
    if len(argv) >= 4: plane.set_view(radius = float(argv[3]))

    scene = JuliaSet(c)
    frame = 0
    redraw = True
    while True:
        if redraw:
            frame += 1
            scene.render(plane, frame)
            redraw = False
            if "RECORD_DIR" in os.environ:
                plane.capture(frame)

        for e in pygame.event.get():
            if e.type not in (KEYDOWN, MOUSEBUTTONDOWN):
                continue
            if e.type == MOUSEBUTTONDOWN:
                plane_coord = plane.convert_to_plane(e.pos)
                if e.button in (1, 3):
                    if e.button == 1:
                        step = 3/4.0
                    else:
                        step = 4/3.0
                    plane.set_view(center = plane_coord, radius = plane.radius * step)
                    redraw = True

            else:
                if e.key == K_ESCAPE:
                    exit(0)
                redraw = True
                if e.key == K_RETURN:
                    scene.c = random.choice(seeds)
                elif e.key in (K_a, K_e):
                    if   e.key == K_a: step = 3/4.0
                    elif e.key == K_e: step = 4/3.0
                    plane.set_view(radius = plane.radius * step)
                elif e.key in (K_z,K_s,K_q,K_d):
                    fact = 20
                    if   e.key == K_z: step = complex(0,  fact/plane.scale[1])
                    elif e.key == K_s: step = complex(0, -fact/plane.scale[1])
                    elif e.key == K_q: step = -fact/plane.scale[0]
                    elif e.key == K_d: step =  fact/plane.scale[0]
                    scene.c += step
                elif e.key in (K_LEFT,K_RIGHT,K_DOWN,K_UP):
                    if   e.key == K_LEFT:  step = -10/plane.scale[0]
                    elif e.key == K_RIGHT: step = +10/plane.scale[0]
                    elif e.key == K_DOWN:  step = complex(0, -10/plane.scale[1])
                    elif e.key == K_UP:    step = complex(0,  10/plane.scale[1])
                    plane.set_view(center = plane.center + step)
                elif e.key == K_r:
                    plane.set_view(center = 0j, radius = 1.5)
                else:
                    redraw = False
                    continue
        clock.tick(25)

if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        pass
