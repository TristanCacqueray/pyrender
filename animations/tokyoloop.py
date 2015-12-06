#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

from utils import *

#constants
WINSIZE = map(lambda x: int(x*SIZE), [ 100,  100])
CENTER  = map(lambda x: x/2, WINSIZE)

MAX_FRAMES = 4524 # 188.5 seconds at 24 fps

PHI = (1+math.sqrt(5))/2.0

lowmod = AudioMod("tokyoloop_lowmono.wav", MAX_FRAMES, filter_type = 1, delay = 15.0)
midmod = AudioMod("tokyoloop_allmono.wav", MAX_FRAMES, filter_type = 2, delay = 20.0)

#lowmod.plot()
#midmod.plot()

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
#        plane.draw_msg("mod %02.3f / %02.3f" % (lowmod.get(frame), midmod.get(frame)), coord = (5, 20))

class MandelbrotSet:
    def __init__(self, escape_limit=1e100, max_iter=69):
        self.escape_limit = escape_limit
        self.max_iter = max_iter

    def render(self, plane):
        start_time = time.time()
        plane.fill((0, 0, 0))
        self.draw_fractal(plane)
        plane.draw_axis()

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


def main(argv):
    frame = 0
    start_frame = 0
    end_frame = MAX_FRAMES
    debug_path = False
    debug_view, debug_radius = -1, 1.5
    if len(argv) >= 2:
        start_frame = int(argv[1])
    if len(argv) >= 3:
        end_frame = int(argv[2])
    if len(argv) >= 4:
        debug_path = True
        if len (argv) == 5:
            debug_view = complex(argv[3])
            debug_radius = float(argv[4])
    if not debug_path and "RECORD_DIR" in os.environ and "PYRENDER_THREAD" not in os.environ:
        os.environ["PYRENDER_THREAD"] = "1"
        parallel_main(start_frame, end_frame)

    scene = JuliaSet()
    clock = pygame.time.Clock()
    plane = ComplexPlane(WINSIZE)

    rad = 3.0
    pos = 0j
    c_values = [-2.3+0j, -1.50+0j, -0.59916666667-0.680515242963j,
            -0.69875-0.47625j,
            -0.56-0.645j,
            -0.58-0.685j,
            -0.10625-0.93375j,
        # beat 1
            -0.157-1.135j,  # item #7
            -0.043-1.087j,
            0.062-0.669j,
            0.152-0.678j,
        # rise 1
        0.425-0.6j,  # item #11
        0.5-0.345j,
        0.488-0.207j,
        0.464-0.135j,
        0.431-0.09j,
        0.386-0.021j,
        0.356-0.003j, # item #17
        # bridge

            -1.40041666667+0.120348576296j, # 840
            -1.34041666667+0.280348576296j, # 
            -0.92041666667+0.360348576296j, # 1040
            -0.76041666667+0.600348576296j,
            -0.52041666667+0.680348576296j,
            -0.28041666667+0.680348576296j,
            ]

    all_c_values = []
    def plot_c_values(start_point = 0, set_view = True):
        if set_view:
            plane.set_view(center = debug_view, radius = debug_radius)
        background = MandelbrotSet()
        background.render(plane)
        idx = start_point
        for c in all_c_values:
            plane.draw_complex(c, (255, 39, 69))
            if (idx+1) in (1, 360, 480, 600, 840, 990, 1140, 1290, 1440, 1639, 1920, 2400, 2610, 2640, 2832, 3024):
                txt_coord = plane.convert_to_screen(c)
                txt_coord[1] -= 10
                plane.draw_msg(str(idx), txt_coord)
            idx += 1
        pygame.display.update()

    while True:
        # Specifics frame settigns
        if frame == 0:
            plane.set_view(radius = rad)

        # Mid freq modulate hue
        scene.hue = 0.48 + 0.13 * midmod.get(frame)

        # Scenes ranges
        if frame >= 4284:
            scene_start = 4284
            scene_len = 240
            if frame == scene_start:
                v_path = N.linspace(plane.center, 0j, scene_len)
                r_path = N.linspace(plane.radius, 1.5, scene_len)
                c_path = []
                path = Path((scene.c, -0.835625+0.2025j), scene_len)
                for c in path.sin(0.005, cycles = 3):
                    c_path.append(c)
            plane.set_view(center = v_path[frame - scene_start], radius = r_path[frame - scene_start])
            scene.c = c_path[frame - scene_start]

        elif frame >= 3804:
            scene_start = 3804
            scene_len = 480
            if frame == scene_start:
                path = Path((scene.c, -0.730625+0.2390625j), scene_len / 2.0)
                c_path = []
                for c in path.sin(0.005, cycles = 2):
                    c_path.append(c)
                final_v = (-0.139582463466-0.0644258872651j)
                v_path = N.linspace(plane.center, final_v, scene_len)
                r_path = N.linspace(plane.radius, 0.05, scene_len)
            mod = complex(0.02 * lowmod.get(frame), 0) #0.001 * midmod.get(frame))
            plane.set_view(center = v_path[frame - scene_start], radius = r_path[frame - scene_start])
            if frame < (scene_start + scene_len / 2.0):
                scene.c = c_path[frame - scene_start] + mod
            else:
                scene.c = c_path[-1] + mod
        elif frame >= 3564: # arp + kick
            scene_start = 3564
            scene_len = 240
            if frame == scene_start:
                path = Path((scene.c, -0.5425+0.6075j, -0.730625+0.2390625j), scene_len)
                c_path = []
                for c in path.sin(0.05, cycles = 5):
                    c_path.append(c)
                r_path = N.linspace(plane.radius, 1.5, scene_len / 3.0)
                v_path = N.linspace(plane.center, 0j, scene_len / 3.0)
            if frame < (scene_start + scene_len / 3.0):
                plane.set_view(center = v_path[frame - scene_start], radius = r_path[frame - scene_start])
            mod = complex(-0.05 * lowmod.get(frame), 0.001 * midmod.get(frame))
            scene.c = c_path[frame - scene_start] + mod
        elif frame >= 3324: # arp
            scene_start = 3324
            scene_len = 240
            if frame == scene_start:
                r_path = N.linspace(plane.radius, 0.2, scene_len)
            plane.set_view(radius = r_path[frame - scene_start])
            mod = complex(0.005 * lowmod.get(frame), 0.001 * midmod.get(frame))
            scene.c = base_c + mod
        elif frame >= 3264: # arp intro
            scene_start = 3264
            scene_len = 60
            if frame == scene_start:
                r_path = N.linspace(plane.radius, 0.08, scene_len)
                base_c = (-0.152091516494+1.029091011j)
            mod = complex(0.005 * lowmod.get(frame), 0.001 * midmod.get(frame))
            #mod = complex(0.01 * lowmod.get(frame), 0)
            plane.set_view(radius = r_path[frame - scene_start])
            scene.c = base_c + mod
        elif frame >= 3024: # 96bpm
            scene_start = 3024
            scene_len = 240
            if frame == scene_start:
                r_path = N.linspace(plane.radius, 0.2, scene_len)
                c_path = []
                bulb_center = -0.1579625+1.033005j
                path = Path((-0.1555325+1.02774j, -0.161405+1.0279425j, -0.1616075+1.0360425j, -0.1543175+1.0372575j, -0.1522925+1.0326j, -0.1543175+1.030575j), scene_len)
                for c in path.sin(0.005, cycles=3):
                    c_path.append(c)
            plane.set_view(radius = r_path[frame - scene_start])
            mod = ((-bulb_center + c_path[frame - scene_start]) / 0.9) * lowmod.get(frame)
            scene.c = c_path[frame - scene_start] + mod

        elif frame >= 2832: # 120bpm Beat loop 2
            scene_len = 192
            if frame == 2832:
                r_path = N.linspace(plane.radius, 0.4, scene_len)
                c_path = []
                bulb_center = -0.125+0.7275j
                path = Path((scene.c,
                    (-0.0390625+0.785625j),
                    (-0.079375+0.66j),
                    (-0.1825+0.6684375j),
                    (-0.2153125+0.7753125j),
                    (-0.1375+0.8353125j),
                    ),
                    scene_len)
                for c in path.splines():
                    c_path.append(c)
            plane.set_view(radius = r_path[frame - 2832])
            mod = ((-bulb_center + c_path[frame - 2832]) / 4.0) * lowmod.get(frame)
            scene.c = c_path[frame - 2832] + mod
        elif frame >= 2640: # 120bpm Beat loop1
            scene_len = 192
            if frame == 2640:
                c_path = []
                bulb_center = -0.125+0.7275j
                path = Path((scene.c, -0.21875+0.71625j, -0.17375+0.823125j, -0.078125+0.82875j, -0.05+0.69j, -0.1325+0.658125j, -0.116875+0.84j), scene_len)
                for c in path.sin(0.01, cycles=3):
                    c_path.append(c)
            mod = ((-bulb_center + c_path[frame - 2640]) / 4.0) * lowmod.get(frame)
            scene.c = c_path[frame - 2640] + mod

        elif frame >= 2580:
            if frame == 2580:
                c_path = []
                path = Path((scene.c, 0.355+0.1425j, 0.25+0.4575j, 0.0475+0.5925j, -0.12828125+0.65015625j), 60)
                for c in path.splines():
                    c_path.append(c)
            mod = complex(0.4 * midmod.get(frame), 0.0004 * lowmod.get(frame))
            scene.c = c_path[frame - 2580] + mod
        elif frame >= 2400:
            if frame == 2400:
                c_path = N.append(
                        N.linspace(scene.c.real, 0.259+0j, 30),
                        N.linspace(0.259+0j, 0.257+0j, 150)
                )
            mod = complex(-0.04 * midmod.get(frame), -0.0004 * lowmod.get(frame))
            scene.c = c_path[frame - 2400] + mod
        elif frame >= 1920:
            if frame == 1920:
                c_path = []
                p = Path([scene.c] + c_values[11:18], 480)
                for c in p.splines():
                    c_path.append(c)
            mod = complex(0.1 * -lowmod.get(frame), 0.05 * midmod.get(frame))
            scene.c = c_path[frame - 1920] + mod
        elif frame >= 1440:
            if frame == 1440:
                c_path = []
                p = Path((scene.c, c_values[7], c_values[8], c_values[9], c_values[10]), 480)
                for c in p.sin(0.02, cycles = 4):
                    c_path.append(c)
            mod = complex(-0.2 * midmod.get(frame), 0.1 * -lowmod.get(frame))
            scene.c = c_path[frame - 1440] + mod
        elif frame >= 840: # Bass intro, move fast to 3rd spot
            if frame == 840:
                c_path = []
                p = Path((scene.c, c_values[3], c_values[4], c_values[5], c_values[6]), 600)
                for c in p.sin(0.04, cycles = 4):
                    c_path.append(c)
                r_path = N.linspace(plane.radius, 2.0, 600)
                v_path = N.linspace(plane.center, 0j, 600)
            plane.set_view(center = v_path[frame - 840], radius = r_path[frame - 840])
            mod = complex(PHI * -0.089 * lowmod.get(frame), 0) #0.001 * lowmod.get(frame))
            scene.c = c_path[frame - 840] + mod
        elif frame >= 600: # Bridge, zoom out, move center to left
            if frame == 600:
                c_path = []
                p = Path((scene.c, c_values[2]), 360)
                for c in p.sin(0.05, cycles = 4):
                    c_path.append(c)
                v_path = N.append(N.linspace(plane.center, 0j, 120), N.linspace(0j, (-0.575-0.21j), 120))
                r_path = N.append(N.append(N.linspace(plane.radius, 1., 120), N.linspace(1., 0.9, 90)), N.linspace(0.9, 0.5, 30))
            plane.set_view(center = v_path[frame-600], radius = r_path[frame-600])
            mod = complex(0, PHI * -0.057 * lowmod.get(frame))
            scene.c = c_path[frame-600] + mod
        elif frame >= 480: # Slow zoom in
            rad -= 1 / 120.0
            plane.set_view(radius = rad)
            mod = complex(0, PHI * 0.057 * lowmod.get(frame))
            scene.c = c_values[1] + mod
        elif frame >= 360:  # Zoom in
            if frame == 360:
                center_path = N.linspace(plane.center, (-0.201083333333-0.0440833333333j), 120)
            rad -= 2.0 / 120.0
            plane.set_view(radius = rad, center = center_path[frame-360])
            scene.c = c_values[1] + complex(0, PHI * 0.15 * lowmod.get(frame))
        elif frame >= 0:
            if frame == 0:
                c_path = N.linspace(c_values[0], c_values[1], 360)
            mod = complex(-0.01, PHI * 0.17 * lowmod.get(frame))
            scene.c = c_path[frame] + mod

        if frame >= start_frame:
            if debug_path:
                all_c_values.append(scene.c)
            else:
                scene.render(plane, frame)
                if "RECORD_DIR" in os.environ:
                    plane.capture(frame)

        frame += 1
        if frame >= end_frame:
            break

        for e in pygame.event.get():
            if  e.type == MOUSEBUTTONDOWN: print plane.convert_to_plane(e.pos)
            elif e.type == KEYDOWN and e.key == K_ESCAPE: exit(0)

    if not debug_path and "MID_RENDER" in os.environ:
        return

    if debug_path:
        plot_c_values(start_frame)

    while True:
        for e in pygame.event.get():
            if e.type not in (KEYDOWN, MOUSEBUTTONDOWN):
                continue
            if e.type == MOUSEBUTTONDOWN:
                plane_coord = plane.convert_to_plane(e.pos)
                print plane_coord
                if e.button in (1, 3):
                    if e.button == 1:
                        step = 0.5
                    else:
                        step = 1.5
                    plane.set_view(center = plane_coord, radius = plane.radius * step)
                    print "'%s' %s" % (plane.center, plane.radius)
                    if debug_path:
                        plot_c_values(start_frame, False)
                    else:
                        scene.render(plane, -1)
        clock.tick(25)


def parallel_main(start_frame, end_frame):
    if (end_frame - start_frame) % 4 != 0:
        print "Wrong frame range..."
        exit(1)
    step = (end_frame - start_frame) / 4
    ranges = range(start_frame, end_frame, step)
    process = []
    os.environ["MID_RENDER"] = "1"
    for i in ranges:
        print "Starting %s %d %d" % (__file__, i, i+step)
        if ranges[-1] == i:
            del os.environ["MID_RENDER"]
        process.append(
            subprocess.Popen([__file__, str(i), str(i+step)])
        )
        time.sleep(0.5)
    for p in process:
        print "return code", p.wait()
    exit(0)


if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        pass
