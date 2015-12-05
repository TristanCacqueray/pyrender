#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

from utils import *

#constants
if "RECORD_DIR" in os.environ:
    SIZE=3
else:
    SIZE=2
WINSIZE = map(lambda x: int(x*SIZE), [ 100,  100])
CENTER  = map(lambda x: x/2, WINSIZE)

MAX_FRAMES = 4524 # 188.5 seconds at 24 fps

PHI = (1+math.sqrt(5))/2.0

lowmod = AudioMod("tokyoloop_lowmono.wav", MAX_FRAMES, filter_type = 1, delay = 15.0)
midmod = AudioMod("tokyoloop_allmono.wav", MAX_FRAMES, filter_type = 2)

#lowmod.plot()
#midmod.plot()

# 
class JuliaSet:
    def __init__(self, c = complex(0, 0), escape_limit = 1e100, max_iter=69, hue = 0.50):
        self.c = 0j
        self.escape_limit = 1e100
        self.max_iter = 69
        self.hue = 0.50

    def render(self, plane, frame):
        start_time = time.time()
        plane.fill((0, 0, 0))
        self.draw_fractal(plane, frame)
        pygame.display.update()
        print "%04d: %.2f sec: c/center/radius = '%s' '%s' %s" % (frame, time.time() - start_time, self.c, plane.center, plane.radius)

    def draw_fractal(self, plane, frame):
        for y in xrange(WINSIZE[1]):
            for x in xrange(WINSIZE[0]):
                z = plane.convert_to_plane((x, y))
                for i in xrange(0, self.max_iter):
                    z = z * z + self.c
                    if abs(z.real) > self.escape_limit or abs(z.imag) > self.escape_limit:
                        break
                if i + 1 == self.max_iter:
                    continue
                hue = self.hue + i / (float(0.89 * self.max_iter))
                color = map(lambda x: x*255, colorsys.hsv_to_rgb(hue, 0.7, 0.7))
                plane.draw_point((x,y), color)

        if False:
            plane.draw_axis()
            # debug, draw dot
            plane.draw_complex(c, (255, 0, 0))

        # debug, draw formula
        if self.c.real >= 0: r_sign = "+"
        else:                r_sign = ""
        if self.c.imag >= 0: i_sign = "+"
        else:                i_sign = ""
        c_str = "[%04d] z*z%s%.5f%s%.5fj" % (frame, r_sign, self.c.real, i_sign, self.c.imag)
        plane.draw_msg(c_str)
        plane.draw_msg("mod %02.3f / %02.3f" % (lowmod.get(frame), midmod.get(frame)), coord = (5, 20))

linear_path=lambda src, dst, start_frame, length, frame: (
    src + (frame - start_frame) * (dst - src) / float(length)
)

def main(argv):
    frame = 0
    start_frame = 0
    end_frame = 3600
    if len(argv) >= 2:
        start_frame = int(argv[1])
    if len(argv) >= 3:
        end_frame = int(argv[2])
    if "RECORD_DIR" in os.environ and "PYRENDER_THREAD" not in os.environ:
        os.environ["PYRENDER_THREAD"] = "1"
        parallel_main(start_frame, end_frame)

    scene = JuliaSet()
    clock = pygame.time.Clock()
    plane = ComplexPlane(WINSIZE)

    rad = 3.0
    pos = 0j
    c_values = [-2.3+0j, -1.50+0j, -1.4+0.120515242963j, -1.28+0.200515242963j,
            -1.40041666667+0.120348576296j, # 840
            -1.34041666667+0.280348576296j, # 
            -0.92041666667+0.360348576296j, # 1040
            -0.76041666667+0.600348576296j,
            -0.52041666667+0.680348576296j,
            -0.28041666667+0.680348576296j,
            ]
    while True:
        # Specifics frame settigns
        if frame == 0: plane.set_view(radius = rad)

        # Scenes ranges
        if frame >= 4524:
            break
        elif frame >= 91320:
            pass
        elif frame >= 9960: # recenter
            rad += 1 / 360.0
            pos += 0.9 / 360.0
            plane.set_view(center = pos, radius = rad)
            mod = complex(-PHI * 0.17 * lowmod.get(frame), -0.01)
            scene.c = c_values[3] + mod
        elif frame >= 840: # Bass intro, move fast to 3rd spot
            s = 100
            pos = (frame - 840) / s
            if pos >= 1 and frame % s <= 6:
                mod *= 1 / (frame % s + 2)
            if frame % s > 6:
                mod = complex(-PHI * 0.05 * lowmod.get(frame), 0)
            scene.c = linear_path(c_values[4+pos], c_values[5+pos], 840 + pos * s, s, frame) + mod
        elif frame >= 600: # Bridge, zoom out, move center to left
            rad += 0.5 / 240.0
            pos -= 0.9 / 240.0
            plane.set_view(center = pos, radius = rad)
            scene.c = linear_path(c_values[1] + mod, c_values[2], 600, 240, frame) #+ mod
        elif frame >= 480: # Slow zoom in
            rad -= 1 / 120.0
            plane.set_view(radius = rad)
            mod = complex(0, PHI * 0.17 * lowmod.get(frame))
            scene.c = c_values[1] + mod
        elif frame >= 360:  # Zoom in
            rad -= 1.5 / 120.0
            plane.set_view(radius = rad)
            scene.c = c_values[1] + complex(0, PHI * 0.17 * lowmod.get(frame))
        elif frame >= 0:    # Move c from -2.4 to -1.5
            mod = complex(0, PHI * 0.17 * lowmod.get(frame))
            scene.c = linear_path(c_values[0], c_values[1], 0, 360, frame) + mod

        # Mid freq modulate hue
        scene.hue = 0.48 + 0.13 * midmod.get(frame)

        if frame >= start_frame:
            scene.render(plane, frame)
            if "RECORD_DIR" in os.environ:
                plane.capture(frame)

        frame += 1
        if frame >= end_frame:
            break

        for e in pygame.event.get():
            if  e.type == MOUSEBUTTONDOWN: print "Clicked", plane.convert_to_plane(e.pos)
            elif e.type == KEYDOWN and e.key == K_ESCAPE: exit(0)


def parallel_main(start_frame, end_frame):
    if (end_frame - start_frame) % 4 != 0:
        print "Wrong frame range..."
        exit(1)
    step = (end_frame - start_frame) / 4
    ranges = range(start_frame, end_frame, step)
    process = []
    for i in ranges:
        print "Starting %s %d %d" % (__file__, i, i+step)
        process.append(
            subprocess.Popen([__file__, str(i), str(i+step)])
        )
        time.sleep(0.5)
    for p in process:
        print "return code", p.wait()
    exit(0)


if __name__ == "__main__":
    main(sys.argv)
