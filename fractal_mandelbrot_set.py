#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

from utils import *

class MandelbrotSet(Window, ComplexPlane):
    def __init__(self, window_size, max_iter=69):
        Window.__init__(self, window_size)
        self.max_iter = float(max_iter)
        self.color_vector = np.vectorize(grayscale_color_factory(self.max_iter))
        self.color_vector = np.vectorize(grayscale_color_factory(self.max_iter))

    def render(self, frame):
        start_time = time.time()
        nparray = compute(complex_fractal, [self.window_size, self.offset, self.scale, self.max_iter, None, self.length])
        self.blit(self.color_vector(nparray))
        self.draw_axis()
        print "%04d: %.2f sec: MandelbrotSet(center/radius = '%s' %s )" % (frame, time.time() - start_time, self.center, self.radius)


pids = set()
def main(argv):
    if len(argv) == 1:
        print "MandelbrotSet explorer"
        print "================="
        print ""
        print "Left/right click to zoom in/out, Middle click to draw JuliaSet"
        print "Use keyboard arrow to move view and r to reset"

    screen = Screen(WINSIZE)
    clock = pygame.time.Clock()
    scene = MandelbrotSet(WINSIZE)
    scene.set_view(center = -0.8, radius = 1.3)
    # Usage allow reuse of frame definition (c, plane center, radius)
    if len(argv) >= 2: scene.set_view(center = complex(argv[1]))
    if len(argv) >= 3: scene.set_view(radius = float(argv[2]))

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
                scene_coord = scene.convert_to_plane(e.pos)
                if e.button in (1, 3):
                    if e.button == 1:
                        step = 0.5
                    else:
                        step = 1.5
                    scene.set_view(center = scene_coord, radius = scene.radius * step)
                    redraw = True
                else:
                    pids.add(subprocess.Popen(["./fractal_julia_set.py", str(scene_coord)]))
            else:
                if e.key == K_ESCAPE:
                    return
                redraw = True
                if e.key in (K_LEFT,K_RIGHT,K_DOWN,K_UP):
                    if   e.key == K_LEFT:  step = -10/scene.scale[0]
                    elif e.key == K_RIGHT: step = +10/scene.scale[0]
                    elif e.key == K_DOWN:  step = complex(0, -10/scene.scale[1])
                    elif e.key == K_UP:    step = complex(0,  10/scene.scale[1])
                    scene.set_view(center = scene.center + step)
                elif e.key == K_r:
                    scene.set_view(center = 0j, radius = 1.5)
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
    pool.terminate()
    pool.join()
    del pool
    for pid in pids:
        pid.terminate()
