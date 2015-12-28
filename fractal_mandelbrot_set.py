#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

# This is a basic Julia set explorer
import math, pygame, os, time, colorsys, sys, random
from pygame.locals import *
import pygame.draw, pygame.image

from utils import *

WINSIZE = map(lambda x: x*SIZE, [ 100,  100])
CENTER  = map(lambda x: x/2, WINSIZE)

scale = lambda x: x / 20.0

PHI=(1+math.sqrt(5))/2.0

class MandelbrotSet:
    def __init__(self, escape_limit=1e100, max_iter=69):
        self.escape_limit = escape_limit
        self.max_iter = max_iter
        self.screen = Screen(WINSIZE)

    def render(self, plane, frame):
        start_time = time.time()
        plane.fill((0, 0, 0))
        self.draw_fractal(plane)
        plane.draw_axis()
        self.screen.display_fullscreen(plane.window)
        print "%04d: %.2f sec: center/radius = '%s' %s" % (frame, time.time() - start_time, plane.center, plane.radius)

    def draw_fractal(self, plane):
        for y in xrange(WINSIZE[1]):
            for x in xrange(WINSIZE[0]):
                c = plane.convert_to_plane((x, y))
                z = 0j
                for i in xrange(0, self.max_iter):
                    z = z * z + c
                    if abs(z.real) > self.escape_limit or abs(z.imag) > self.escape_limit:
                        break
                if i + 1 == self.max_iter:
                    continue
                color = tuple([255 * i / float(self.max_iter)] * 3)
                plane.draw_point((x,y), color)


pids = set()
def main(argv):
    if len(argv) == 1:
        print "MandelbrotSet explorer"
        print "================="
        print ""
        print "Left/right click to zoom in/out, Middle click to draw JuliaSet"
        print "Use keyboard arrow to move view and r to reset"

    pygame.init()
    clock = pygame.time.Clock()
    plane = ComplexPlane(WINSIZE)
    plane.set_view(center = -0.8)
    # Usage allow reuse of frame definition (c, plane center, radius)
    if len(argv) >= 2: plane.set_view(center = complex(argv[1]))
    if len(argv) >= 3: plane.set_view(radius = float(argv[2]))

    scene = MandelbrotSet()
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
                        step = 0.5
                    else:
                        step = 1.5
                    plane.set_view(center = plane_coord, radius = plane.radius * step)
                    redraw = True
                else:
                    pids.add(subprocess.Popen(["./fractal_julia_set.py", str(plane_coord)]))
            else:
                if e.key == K_ESCAPE:
                    return
                redraw = True
                if e.key in (K_LEFT,K_RIGHT,K_DOWN,K_UP):
                    if   e.key == K_LEFT:  step = -10/plane.scale[0]
                    elif e.key == K_RIGHT: step = +10/plane.scale[0]
                    elif e.key == K_DOWN:  step = complex(0, -10/plane.scale[1])
                    elif e.key == K_UP:    step = complex(0,  10/plane.scale[1])
                    plane.set_view(center = plane.center + step)
                elif e.key == K_r:
                    plane.set_view(center = 0j, radius = 1.5)
                else:
                    redraw = False
                    print
                    continue
        clock.tick(25)

if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        pass
    for pid in pids:
        pid.terminate()
