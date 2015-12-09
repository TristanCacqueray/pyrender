#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

from utils import *

#constants
WINSIZE = map(lambda x: int(x*SIZE), [ 100,  100])
CENTER  = map(lambda x: x/2, WINSIZE)

MAX_FRAMES = 4524 # 188.5 seconds at 24 fps

PHI = (1+math.sqrt(5))/2.0

# for headless rendering
# export SDL_VIDEODRIVER=dummy
# export SDL_AUDIODRIVER=dummy

lowmod = AudioMod("tokyoloop_lowmono.wav", MAX_FRAMES, filter_type = 1, delay = 15.0)
midmod = AudioMod("tokyoloop_allmono.wav", MAX_FRAMES, filter_type = 2, delay = 20.0)

#lowmod.plot()
#midmod.plot()

class JuliaSet:
    def __init__(self):
        self.c = 0j
        self.escape_limit = 1e150
        self.max_iter = 69 * 6
        self.effective_max_iter = 69
        self.hue = 0.40

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
                for i in xrange(0, self.effective_max_iter):
                    z = z * z + self.c
                    if abs(z.real) > self.escape_limit or abs(z.imag) > self.escape_limit:
                        break
                if i + 1 == self.effective_max_iter:
                    continue
                hue = self.hue + i / (0.1 * self.max_iter)
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
#        plane.draw_msg(c_str)
#        plane.draw_msg("mod %02.3f / %02.3f" % (lowmod.get(frame), midmod.get(frame)), coord = (5, 20))


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

    all_c_values = []
    def plot_c_values(start_point = 0, set_view = True):
        if set_view:
            plane.set_view(center = debug_view, radius = debug_radius)

        # Draw mandelbrotset background
        plane.fill((0, 0, 0))
        for y in xrange(WINSIZE[1]):
            for x in xrange(WINSIZE[0]):
                c = plane.convert_to_plane((x, y))
                z = 0j
                for i in xrange(0, 69):
                    z = z * z + c
                    if abs(z.real) > 1e100 or abs(z.imag) > 1e100:
                        break
                if i + 1 == 69:
                    continue
                color = tuple([255 * i / 69.] * 3)
                plane.draw_point((x,y), color)
        plane.draw_axis()

        idx = start_point
        for c in all_c_values:
            plane.draw_complex(c, (255, 39, 255))
            if (idx+1) in (1, 360, 480, 600, 840, 1080, 1320, 1440, 1639, 1824, 1920, 2100, 2187, 2246, 2400, 2610, 2640, 2832, 3024):
                txt_coord = plane.convert_to_screen(c)
                txt_coord[1] -= 10
                plane.draw_msg(str(idx), txt_coord)
            idx += 1
        pygame.display.update()

    while True:
        # Animation 'scenes' description bellow:

        if frame >= 4524: # phade out
            scene_start, scene_len = 4524, 30
            plane.set_view(radius = radius_path[frame - scene_start])

        if frame >= 4284: # Last zoom out
            scene_start, scene_len = 4284, 240.
            if frame == scene_start:
                center_path = N.linspace(plane.center, 0j, scene_len)
                radius_path = N.linspace(plane.radius, 3.5, (scene_len + 30))
                c_path = []
                path = Path((scene.c, -0.835625+0.2025j), scene_len)
                for c in path.sin(0.005, cycles = 3):
                    c_path.append(c)
            plane.set_view(center = center_path[frame - scene_start], radius = radius_path[frame - scene_start])
            scene.c = c_path[frame - scene_start]

        elif frame >= 3804: # Last dive
            scene_start, scene_len = 3804, 480.
            if frame == scene_start:
                c_path = Path((scene.c, -0.730625+0.2390625j), scene_len / 2.0).sin(0.005, cycles = 2)
                final_v = -0.159169507972-0.0692542695555j
                center_path = N.linspace(plane.center, final_v, scene_len)
                radius_path = N.linspace(plane.radius, 0.01, scene_len)
            mod = complex(0.02 * lowmod.get(frame), 0) #0.001 * midmod.get(frame))
            plane.set_view(center = center_path[frame - scene_start], radius = radius_path[frame - scene_start])
            if frame < (scene_start + scene_len / 2.0):
                scene.c = c_path[frame - scene_start] + mod
            elif frame <= 4267:
                scene.c = c_path[-1] + mod

        elif frame >= 3564: # arp + kick
            scene_start, scene_len = 3564, 240.
            if frame == scene_start:
                path = Path((scene.c, -0.5425+0.6075j, -0.730625+0.2390625j), scene_len)
                c_path = []
                for c in path.sin(0.05, cycles = 5):
                    c_path.append(c)
                radius_path = N.linspace(plane.radius, 1.8, scene_len / 3.0)
                center_path = N.linspace(plane.center, 0j, scene_len / 3.0)
            if frame < (scene_start + scene_len / 3.0):
                plane.set_view(center = center_path[frame - scene_start], radius = radius_path[frame - scene_start])
            mod = complex(-0.08 * lowmod.get(frame), 0.01 * midmod.get(frame))
            scene.c = c_path[frame - scene_start] + mod

        elif frame >= 3324: # arp
            scene_start, scene_len = 3324, 240.
            if frame == scene_start:
                radius_path = N.linspace(plane.radius, 0.2, scene_len)
            plane.set_view(radius = radius_path[frame - scene_start])
            mod = complex(0.005 * lowmod.get(frame), 0.001 * midmod.get(frame))
            scene.c = base_c + mod

        elif frame >= 3264: # arp intro
            scene_start, scene_len = 3264, 60.
            if frame == scene_start:
                radius_path = N.linspace(plane.radius, 0.1, scene_len)
                base_c = (-0.152091516494+1.029091011j)
            mod = complex(0.005 * lowmod.get(frame), 0.001 * midmod.get(frame))
            #mod = complex(0.01 * lowmod.get(frame), 0)
            plane.set_view(radius = radius_path[frame - scene_start])
            scene.c = base_c + mod

        elif frame >= 3024: # 96bpm
            scene_start, scene_len = 3024, 240.
            if frame == scene_start:
                radius_path = N.linspace(plane.radius, 0.2, scene_len)
                bulb_center = -0.1579625+1.033005j
                c_path = Path((-0.1555325+1.02774j, -0.161405+1.0279425j, -0.1616075+1.0360425j, -0.1543175+1.0372575j,
                    -0.1522925+1.0326j, -0.1543175+1.030575j), scene_len).sin(0.005, cycles=3)
            plane.set_view(radius = radius_path[frame - scene_start])
            mod = ((-bulb_center + c_path[frame - scene_start]) / 0.9) * lowmod.get(frame)
            scene.c = c_path[frame - scene_start] + mod

        elif frame >= 2832: # 120bpm Beat loop 2
            scene_start, scene_len = 2832, 192
            if frame == scene_start:
                radius_path = N.linspace(plane.radius, 0.4, scene_len)
                bulb_center = -0.125+0.7275j
                c_path = Path((scene.c,
                    (-0.0390625+0.785625j),
                    (-0.079375+0.66j),
                    (-0.1825+0.6684375j),
                    (-0.2153125+0.7753125j),
                    (-0.1375+0.8353125j),
                    ),
                    scene_len).splines()
            plane.set_view(radius = radius_path[frame - scene_start])
            mod = ((bulb_center - c_path[frame - scene_start]) / 3.0) * lowmod.get(frame)
            scene.c = c_path[frame - 2832] + mod

        elif frame >= 2640: # 120bpm Beat loop1
            scene_start, scene_len = 2640, 192
            if frame == scene_start:
                bulb_center = -0.125+0.7275j
                c_path = Path((scene.c, -0.21875+0.71625j, -0.17375+0.823125j, -0.078125+0.82875j, -0.05+0.69j, -0.1325+0.658125j, -0.116875+0.84j),
                        scene_len).sin(0.008, cycles=3)
            mod = ((bulb_center - c_path[frame - scene_start]) / 3.0) * lowmod.get(frame)
            scene.c = c_path[frame - scene_start] + mod

        elif frame >= 2580: # quickly go to P1
            scene_start, scene_len = 2580, 60.
            if frame == 2580:
                c_path = Path((scene.c, 0.355+0.1425j, 0.25+0.4575j, 0.0475+0.5925j, -0.10828125+0.638j), scene_len).splines()
            mod = complex(0.05 * lowmod.get(frame), 0.0004 * midmod.get(frame)) + complex(0.08 * lowmod.get(frame), 0.025)
            scene.c = c_path[frame - scene_start] + mod

        elif frame >= 2400: # slowly move c from 0.259 to 0.257
            scene_start, scene_len = 2400, 180.
            if frame == 2400:
                c_path = N.append(
                        N.linspace(scene.c.real, 0.259+0j, 30),
                        N.linspace(0.259+0j, 0.257+0j, 150)
                )
            mod = complex(-0.02 * midmod.get(frame), -0.0004 * lowmod.get(frame))
            scene.c = c_path[frame - scene_start] + mod

        elif frame >= 1920: # rise, contour to center pole
            scene_start, scene_len = 1920, 480.
            if frame == scene_start:
                c_path = Path((scene.c,
                                0.425-0.6j,  # item #11
                                0.5-0.345j,
                                0.488-0.207j,
                                0.489-0.135j,
                                0.449-0.09j,
                                0.41-0.031j,
                                0.356-0.005j, # item #17
                        ), scene_len).splines()
                radius_path = N.linspace(plane.radius, 1.3, scene_len)
                center_path = N.linspace(plane.center, 0j,  scene_len)
            plane.set_view(center = center_path[frame - scene_start], radius = radius_path[frame - scene_start])
            mod = complex(0.1 * -lowmod.get(frame), 0.05 * midmod.get(frame))
            scene.c = c_path[frame - scene_start] + mod

        elif frame >= 1440: # New beat
            scene_start, scene_len = 1440, 480.
            if frame == scene_start:
                c_path = Path((scene.c, -0.157-1.105j, -0.107-1.08j, 0.062-0.75j, 0.152-0.75j), scene_len).sin(0.02, cycles = 4)
            mod = complex(0.1 * midmod.get(frame), 0.1 * lowmod.get(frame))
            scene.c = c_path[frame - scene_start] + mod

        elif frame >= 1320: # Bass fades
            scene_start, scene_len = 1320, 120.
            if frame == scene_start:
                radius_path = N.linspace(plane.radius, 1., scene_len)
                center_path = N.linspace(plane.center, -0.5-0.25j,  scene_len)
                c_path = N.linspace(scene.c, -0.23-1j, scene_len)
            plane.set_view(center = center_path[frame - scene_start], radius = radius_path[frame - scene_start])
            mod = complex(0.09 * lowmod.get(frame), 0.089 * midmod.get(frame))
            scene.c = c_path[frame - scene_start] + mod

        elif frame >= 1080: # Bass cont
            scene_start, scene_len = 1080, 240.
            if frame == scene_start:
                c_path = Path((scene.c, -0.388325195312-0.758092773438j, -0.288657226563-0.979594726563j), scene_len).sin(0.005, cycles = 3)
                radius_path = N.linspace(plane.radius, 1.5, scene_len)
                center_path = N.linspace(plane.center, 0j,  scene_len)
            plane.set_view(center = center_path[frame - scene_start], radius = radius_path[frame - scene_start])
            mod = complex(0.15 * midmod.get(frame), 0.08 * lowmod.get(frame))
            scene.c = c_path[frame - scene_start] + mod

        elif frame >= 840: # Bass intro, move fast to 3rd spot
            scene_start, scene_len = 840, 240.
            if frame == scene_start:
                c_path = Path((scene.c, -0.69875-0.47625j, -0.56-0.685j), scene_len).sin(0.01, cycles = 5)
                radius_path = N.linspace(plane.radius, 1.5, scene_len * 2)
                center_path = N.linspace(plane.center, 0j,  scene_len * 2)
            plane.set_view(center = center_path[frame - scene_start], radius = radius_path[frame - scene_start])
            mod = complex(-0.08 * lowmod.get(frame), -0.03 * midmod.get(frame))
            scene.c = c_path[frame - scene_start] + mod

        elif frame >= 600: # Bridge, zoom out, move center to left
            scene_start, scene_len = 600, 240.
            if frame == scene_start:
                #c_path = Path((scene.c, -0.59916666667-0.680515242963j), 360).sin(0.05, cycles = 4, sign = -1)

                c_path = Path((scene.c, -1.4-0.12j, -1.19375-0.31875j, -1.0175-0.37875j, -0.8115625-0.39j), scene_len).sin(0.01, cycles = 3)
                center_path = N.append(N.linspace(plane.center, 0j, 120), N.linspace(0j, -0.55-0.1925j, 120))
                radius_path = N.append(N.append(N.linspace(plane.radius, 1., 120), N.linspace(1., 1., 30)), N.linspace(1., 0.5, 90))
            plane.set_view(center = center_path[frame-scene_start], radius = radius_path[frame-scene_start])
            #mod = complex(0, -0.3 * lowmod.get(frame))
            mod = complex(0, PHI * -0.057 * lowmod.get(frame))
            scene.c = c_path[frame - scene_start] + mod

        elif frame >= 480: # Fast zoom in
            scene_start, scene_len = 480, 120.
            if frame == scene_start:
                radius_path = N.linspace(plane.radius, 0.1, scene_len)
            plane.set_view(radius = radius_path[frame - scene_start])
            mod = complex(0, PHI * -0.057 * lowmod.get(frame))
            scene.c = c_path[-1] + mod

        elif frame >= 360:  # Zoom in, moved to -0.201-0.044j
            scene_start, scene_len = 360, 120.
            if frame == scene_start:
                center_path = N.linspace(plane.center, -0.145348958333-0.0328020833333j, scene_len)
                radius_path = N.linspace(plane.radius, 2.0, scene_len)
            plane.set_view(radius = radius_path[frame - scene_start], center = center_path[frame - scene_start])
            scene.c = c_path[-1] + complex(0, PHI * -0.15 * lowmod.get(frame))

        elif frame >= 0:    # Intro, translate from -2.3 to -1.42
            scene_start, scene_len = 0, 360.
            if frame == scene_start:
                plane.set_view(center = 0j, radius = 3.0)
                c_path = N.linspace(-2.3+0j, -1.42+0j, scene_len)
            mod = complex(-0.01, PHI * -0.17 * lowmod.get(frame))
            scene.c = c_path[frame -scene_len] + mod


        # Mid freq modulate hue
        # scene.hue = 0.40 + 0.13 * math.log10(1 + 9 * midmod.get(frame))
        # print midmod.get(frame), math.log10(1 + 9 * midmod.get(frame))
        # scene.hue = 0.40 + 0.13 * lowmod.get(frame)


        if frame >= start_frame:
            all_c_values.append(scene.c)
            if not debug_path:
                scene.render(plane, frame)
                if "RECORD_DIR" in os.environ:
                    plane.capture(frame)

        frame += 1
        if frame >= end_frame:
            break

        for e in pygame.event.get():
            if  e.type == MOUSEBUTTONDOWN: print plane.convert_to_plane(e.pos)
            elif e.type == KEYDOWN and e.key == K_ESCAPE: exit(0)

    if not debug_path: #and "MID_RENDER" in os.environ:
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
    if (end_frame - start_frame) % multiprocessing.cpu_count() != 0:
        print "Wrong frame range..."
        exit(1)
    step = (end_frame - start_frame) / multiprocessing.cpu_count()
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
