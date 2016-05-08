#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

# This is a basic MarkusLyapunov space explorer
from utils import *


class MarkusLyapunov(Window, ComplexPlane):
    def __init__(self, window_size, seed):
        Window.__init__(self, window_size)
        self.seed = seed
        self.x0 = 0.5
        self.max_iter = 100 # 800
        self.max_init = 50 # 400
        self.seed_values = seed * (int(max(self.max_iter, self.max_init) / float(len(self.seed))) + 1)
        self.colorize = bright_color_factory(10)
        #self.set_view(4+4j, 4)
        self.set_view(0j, 4)

    def render(self, frame):
        start_time = time.time()
        for i in xrange(self.length):
            x_pos, y_pos = i / self.window_size[1], i % self.window_size[1]
            c = self.convert_to_plane((x_pos + 1, y_pos))
            markus_func = lambda x: c.real if self.seed_values[idx] == "A" else c.imag

            # Init
            x = self.x0
            for idx in xrange(1, self.max_init):
                r = markus_func(idx)
                x = r * x * ( 1 - x )

            # Exponent
            total = 0
            for idx in range(1, self.max_iter):
                r = markus_func(idx)
                x = r * x * ( 1 - x )
                v = abs(r - 2 * r * x)
                if v == 0:
                    v = 1e-6
                total = total + math.log(v) / math.log(2)
            exponent = total / float(self.max_iter)
            if exponent == float('Inf'):
                exponent = 0

            self.draw_point((x_pos, y_pos), self.colorize(exponent))
        print "%04d: %.2f sec: MarkusLyapunov(seed/center/radius = '%s' '%s' %s )" % (frame, time.time() - start_time, self.seed, self.center, self.radius)


def main(argv):
    if len(argv) == 1:
        print "Markus-Lyapunov explorer"
        print "========================"
        print ""
        print "Click the window to center"
        print "Use keyboard arrow to move window, 'a'/'e' to zoom in/out, 'r' to reset view"

    pygame.init()
    screen = Screen(WINSIZE)
    clock = pygame.time.Clock()

    scene = MarkusLyapunov(WINSIZE, "AB")
    screen.add(scene)
    frame = 0
    redraw = True
    while True:
        if redraw:
            frame += 1
            scene.render(frame)
            screen.update()
            pygame.display.update()
            redraw = False
            if "RECORD_DIR" in os.environ:
                screen.capture(frame, os.environ["RECORD_DIR"])

        for e in pygame.event.get():
            if e.type not in (KEYDOWN, MOUSEBUTTONDOWN):
                continue
            if e.type == MOUSEBUTTONDOWN:
                plane_coord = scene.convert_to_plane(e.pos)
                if e.button in (1, 3):
                    if e.button == 1:
                        step = 3/4.0
                    else:
                        step = 4/3.0
                    scene.set_view(center = plane_coord, radius = scene.radius * step)
                    redraw = True
                else:
                    print "Clicked", e.pos
            else:
                if e.key == K_ESCAPE:
                    exit(0)
                redraw = True
                if e.key == K_RETURN:
                    scene.c = random.choice(seeds)
                elif e.key in (K_a, K_e):
                    if   e.key == K_a: step = 3/4.0
                    elif e.key == K_e: step = 4/3.0
                    scene.set_view(radius = scene.radius * step)
                elif e.key in (K_LEFT,K_RIGHT,K_DOWN,K_UP):
                    if   e.key == K_LEFT:  step = -10/scene.scale[0]
                    elif e.key == K_RIGHT: step = +10/scene.scale[0]
                    elif e.key == K_DOWN:  step = complex(0, -10/scene.scale[1])
                    elif e.key == K_UP:    step = complex(0,  10/scene.scale[1])
                    scene.set_view(center = scene.center + step)
                elif e.key == K_r:
                    scene.set_view(center = 4+4j, radius = 4)
                else:
                    redraw = False
                    continue
        clock.tick(25)

if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        pass
    pool.terminate()
    pool.join()
    del pool
