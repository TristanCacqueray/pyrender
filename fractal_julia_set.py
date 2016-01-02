#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

# This is a basic Julia set explorer
from utils import *


class JuliaSet(Window, ComplexPlane):
    def __init__(self, window_size, c = complex(0, 0), escape_limit=1e100, max_iter=69):
        Window.__init__(self, window_size)
        self.c = c
        self.max_iter = 69.
        self.color_vector = np.vectorize(grayscale_color_factory(self.max_iter))
        self.set_view(0j, 3)

    def render(self, frame):
        start_time = time.time()
        nparray = compute(complex_fractal, [self.window_size, self.offset, self.scale, self.max_iter, self.c, self.length])
        self.blit(self.color_vector(nparray))
        self.draw_axis()
        self.draw_function_msg()
        self.draw_cpoint()
        print "%04d: %.2f sec: JuliaSet(c/center/radius = '%s' '%s' %s )" % (frame, time.time() - start_time, self.c, self.center, self.radius)

    def draw_function_msg(self):
        if self.c.real >= 0: r_sign = "+"
        else:                r_sign = ""
        if self.c.imag >= 0: i_sign = "+"
        else:                i_sign = ""
        self.c_str = "z*z%s%.5f%s%.5fj" % (r_sign, self.c.real, i_sign, self.c.imag)
        self.draw_msg(self.c_str)

    def draw_cpoint(self):
        self.draw_complex(self.c, (255, 0, 0))

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
    screen = Screen(WINSIZE)
    clock = pygame.time.Clock()
    c = random.choice(seeds)
    # Usage allow reuse of frame definition (c, plane center, radius)
    if len(argv) >= 2: c = complex(argv[1])
    if len(argv) >= 3: scene.set_view(center = complex(argv[2]))
    if len(argv) >= 4: scene.set_view(radius = float(argv[3]))

    scene = JuliaSet(WINSIZE, c)
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
                elif e.key in (K_z,K_s,K_q,K_d):
                    fact = 20
                    if   e.key == K_z: step = complex(0,  fact/scene.scale[1])
                    elif e.key == K_s: step = complex(0, -fact/scene.scale[1])
                    elif e.key == K_q: step = -fact/scene.scale[0]
                    elif e.key == K_d: step =  fact/scene.scale[0]
                    scene.c += step
                elif e.key in (K_LEFT,K_RIGHT,K_DOWN,K_UP):
                    if   e.key == K_LEFT:  step = -10/scene.scale[0]
                    elif e.key == K_RIGHT: step = +10/scene.scale[0]
                    elif e.key == K_DOWN:  step = complex(0, -10/scene.scale[1])
                    elif e.key == K_UP:    step = complex(0,  10/scene.scale[1])
                    scene.set_view(center = scene.center + step)
                elif e.key == K_r:
                    scene.set_view(center = 0j, radius = 1.5)
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
