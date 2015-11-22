#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

# This is a basic Julia set explorer
import math, pygame, os, time, colorsys, sys
from pygame.locals import *
import pygame.draw, pygame.image

#constants
WINSIZE = map(lambda x: x*3, [ 160,  160])
CENTER  = map(lambda x: x/2, WINSIZE)

scale = lambda x: x / 20.0

MAX=1e100
ITER=23

class JuliaRender:
    def __init__(self, c):
        self.c = c

    def draw(self, plane):
        for y in plane.range(1):
            for x in plane.range(0):
                coord = (x, y)
                z = complex(*coord)
                for i in xrange(0, ITER):
                    z = z * z + self.c
                    if abs(z.real) > MAX or abs(z.imag) > MAX:
                        break
                if i + 1 == ITER:
                    color = (0, 0, 0)
                else:
                    color = tuple([255 * i / float(ITER)] * 3)
                plane.draw_point(coord, color)

class Plane:
    def __init__(self, screen_size, plane_min, plane_max, zoom = 1):
        self.screen = pygame.display.set_mode(screen_size)
        self.screen_size = screen_size
        self.zoom = zoom
        self.plane_size = (plane_min, plane_max)
        plane_min = map(float, plane_min)
        plane_max = map(float, plane_max)
        # Coordinate conversion vector
        self.offset = (abs(plane_min[0]), abs(plane_min[1]))
        self.scale = (
            self.screen_size[0] / float(plane_max[0] - plane_min[0]),
            self.screen_size[1] / float(plane_max[1] - plane_min[1])
        )
        self.step = (
            (plane_max[0] - plane_min[0]) / float(self.screen_size[0]),
            (plane_max[1] - plane_min[1]) / float(self.screen_size[1])
        )

    def fill(self, color):
        self.screen.fill(color)

    def range(self, axis):
        pos = self.plane_size[0][axis]
        stop = self.plane_size[1][axis]
        step = self.step[axis] * self.zoom
        while pos < stop:
            yield pos
            pos += step

    def draw_point(self, coord, color):
        screen_coord = (
            int((coord[0] + self.offset[0]) * self.scale[0]),
            self.screen_size[1] - int((coord[1] + self.offset[1]) * self.scale[1])
        )
        #print "Drawing\t", coord, "at", plane_coord
        self.screen.set_at(screen_coord, color)

    def draw_msg(self, msg, coord = (5, 770), color = (180, 180, 255)):
        text = font.render(msg, True, color)
        self.screen.blit(text, coord)


#clock = pygame.time.Clock()
pygame.init()
font = pygame.font.SysFont(u'dejavusansmono', 24)

v = Plane(WINSIZE, (-3, -3), (3, 3))

c = complex(0, 0)
step = complex(0.025, 0.025)
while True:
    v.fill((0, 0, 0))

    print "z * z +", c, "\t(step =", step, ")"
    scene = JuliaRender(c)
    scene.draw(v)

    v.draw_msg("Up/Down:    change imag step", coord = (5, 5))
    v.draw_msg("Left/Right: change real step", coord = (5, 20))
    pygame.display.update()

    #time.sleep(0.5)
    for e in pygame.event.get():
        if e.type != KEYUP:
            continue
        if e.key == K_ESCAPE:
            exit(0)
        if e.key == K_UP:
            step += 0.05j
        elif e.key == K_DOWN:
            step -= 0.05j
        if e.key == K_LEFT:
            step -= 0.05
        elif e.key == K_RIGHT:
            step += 0.05

    c += step
#    clock.tick(25)
