#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

from utils import *

#constants
WAV_WIDTH = int(WINSIZE[0] / 5)
MOD_WIDTH = int(WINSIZE[0] / 5)
SG_HEIGHT = int(WINSIZE[1] / 5)

FADEIN_LENGTH = 69
FADEOUT_LENGTH = 120

# Audio mod generator
class Fractal(ScreenPart, ComplexPlane):
    def __init__(self, window_size, c = None, color_vector = bright_color_factory):
        ScreenPart.__init__(self, window_size)
        self.c = c
        self.set_view(0j, 1)
        self.max_iter = 73.
        self.hue = 0.5
        self.last_view = None
        self.color_vector = color_vector

    def draw_complex(self, plane_coord, color = 0xffffff):
        coord = (int((plane_coord.real - self.offset[0]) * self.scale[0]),
                        self.window_size[1] - int((plane_coord.imag - self.offset[1]) * self.scale[1]))
        if coord[0] < 0 or coord[1] < 0 or coord[1] >= self.pixels.shape[1] or coord[0] >= self.pixels.shape[0]:
            return
        self.pixels[coord[0]][coord[1]] = color

    def render(self):
        if not self.window_size[0]:
            return
        if self.c is None:
            if (self.center, self.radius) == self.last_view:
                # Reuse pre-render
                self.pixels = self.pixels_copy.copy()
                return
            self.last_view = (self.center, self.radius)
        nparray = compute(complex_fractal, [self.window_size, self.offset, self.scale, self.max_iter, self.c, self.length])
        nparray = np.vectorize(self.color_vector(self.max_iter, self.hue))(nparray)
        self.pixels = nparray.reshape(*self.window_size)
        if self.c is None: # Keep mandelbrot render
            self.pixels_copy = self.pixels.copy()

BULB_2_CENTER=(-0.119357142857+0.739607142857j)
BULB_3_CENTER=(-0.502214285714+0.563857142857j)
BULB_3_VIEW=(-0.369214285714+0.700857142857j)
SULB_3_CENTER=(-0.535214285714+0.604571428571j)
KULB_3_CENTER=(-0.563214285714+0.642571428571j)

FREQS = [
    #v,  range,      clip, scale, decay
    [0., (250, 350), 0.1, 1., 4.],
    [0., (150, 190), None, 1., 10.],
    [0., (7, 9), 0.6, 2., 15.], # Low freq
]
HIGHF=0
MIDF=1
LOWF=2

class Modulator(ScreenPart):
    def __init__(self, window_size, bpm, fps, end_frame, args):
        ScreenPart.__init__(self, window_size)
        self.freqs = FREQS
        self.c_num_draw = 42
        self.c_values = []
        self.fps = fps
        self.args = args
        self.scale = fps * 4 * 60 / bpm

        self.high_speed = 0
        self.mid_speed = 0
        self.angle = 0
        self.min_angle = 0
        self.max_angle = 360
        self.sign = 1
        self.scenes = [
            [end_frame, self.fadeout],
            #[4457,      self.ending],
            [3542,      self.end_th],
            [3314,      self.brk04],
            [2857,      self.deep_th],
            [2628,      self.brk03],
            [1942,      self.main_th],
            [1828,      self.brk02],
            [914,       self.bass_th],
            [857,       self.brk01],
            [228,       self.intro_t],
            [0,         self.bells],
            [-FADEIN_LENGTH, self.fadein],
        ]
        self.scenes_name = {}
        for idx in xrange(len(self.scenes)):
            scene = self.scenes[idx]
            scene[0] += FADEIN_LENGTH
            if idx == 0:
                scene_length = FADEOUT_LENGTH
            else:
                scene_length = self.scenes[idx - 1][0] - scene[0]
            scene.insert(1, float(scene_length))
            self.scenes_name[scene[-1].func_name] = scene[:2]

        # States
        self.scales = [[0, 0], [0, 0]]
        self.lspaces = {}

    def move_view(self, ft, center = None, radius = None, length = None, pos = None):
        idx = 1
        if length is None:
            length = self.scene_length
        if pos is None:
            pos = self.scene_pos
        if (pos+1) >= length:
            return
        if ft.c is None:
            idx = 0
        if center is not None:
            if pos == 0:
                self.scales[idx][0] = np.linspace(ft.center, center, length)
            center = self.scales[idx][0][pos]
        if radius is not None:
            if pos == 0:
                self.scales[idx][1] = np.linspace(ft.radius, radius, length)
                #self.scales[idx][1] = np.logspace(np.log10(ft.radius), np.log10(radius), length)
                #self.scales[idx][1] = np.logspace(np.log10(ft.radius), np.log10(radius), length)
            radius = self.scales[idx][1][pos]
        ft.set_view(center = center, radius = radius)

    def update(self, frame, spectrogram, main_ft, debug_ft):
        # Update mods
        for freq in self.freqs:
            current, freq_range, clip, scale, decay = freq
            if not freq_range:
                continue
            vals = spectrogram.freq[freq_range[0]:freq_range[1]]
            val = np.median(vals)
            if clip:
                val = max(0, val - clip)
            val = min(1., val * scale)
            if val > current:
                freq[0] = val
            else:
                freq[0] -= (current - val) / decay

        self.high_speed -= self.high_speed / 12.
        self.high_speed = min(1, self.high_speed + (1 - self.high_speed) / 3. * self.freqs[0][0])
        self.mid_speed -= self.mid_speed / 4.
        self.mid_speed = min(1, self.mid_speed + (1. - self.mid_speed) / 4. * self.freqs[1][0])

        self.draw_point = [
            (self.freqs[HIGHF][0], self.high_speed, 0x008080),
            (self.freqs[MIDF][0], self.mid_speed, 0x80ff80),
            (self.freqs[LOWF][0], None, 0xff0000),
        ]

        # Update angle direction
        if self.angle >= self.max_angle:
            self.sign = -1
        elif self.angle < self.min_angle:
            self.sign = 1

        # Find scene
        for idx in xrange(len(self.scenes)):
            if frame >= self.scenes[idx][0]:
                self.scene_start, self.scene_length, scene_update = self.scenes[idx]
                self.scene_pos = frame - self.scene_start
                self.scene_init = self.scene_pos == 0
                break
        if idx == len(self.scenes):
            print "could not find scene %d" % frame
            exit(1)

        self.main_ft = main_ft
        self.debug_ft = debug_ft
        self.frame = frame
        scene_update()
        self.c_values.insert(0, main_ft.c)
        return scene_update.func_name

    def solve(self, c):
        i = 0
        u = c
        while i < self.max_iter:
            u = u * u + c
            if abs(u.real) > 1e100 or abs(u.imag) > 1e100:
                break
            i += 1
        if i >= (self.max_iter - 3):
            return False
        return True

    def linspace(self, start, stop, length = None, pos = None):
        if length is None: length = self.scene_length
        if pos is None: pos = self.scene_pos
        idx = (stop, length)
        if pos == 0:
            self.lspaces[idx] = np.linspace(start, stop, length)
        return self.lspaces[idx][pos]

    ########
    # Scenes
    def fadein(self):
        if self.scene_init:
            self.main_ft.set_view(center = 0j, radius = 3.0)
            self.debug_ft.set_view(center = 0j, radius = 1.5)
            self.fadein_radius = 1.3
            self.main_ft.c = 1+1.3j
            self.fadein_zoom_length = self.scenes_name["bells"][1] + self.scenes_name["fadein"][1]

        # Zoom in for the next 2 scenes
        self.move_view(self.main_ft, radius = self.fadein_radius, length = self.fadein_zoom_length, pos = self.frame)
        self.move_view(self.debug_ft, center = BULB_2_CENTER, radius=0.3)
        self.main_ft.c = self.linspace(self.main_ft.c, BULB_2_CENTER + 0.13)

    def bells(self):
        if self.scene_init:
            self.mod_center = self.main_ft.c

        # Keep on zooming
        self.move_view(self.main_ft, radius = self.fadein_radius, length = self.fadein_zoom_length, pos = self.frame)
        x_scale, y_scale = self.main_ft.radius / 3., self.main_ft.radius / 2.
        # Move c along x * lowfreq, y * midfreq~highfreq
        m = complex(0, y_scale * self.freqs[MIDF][0])
        m += complex(self.freqs[LOWF][0] * x_scale / 2.)
        m += complex(-self.freqs[HIGHF][0] * x_scale)
        new_c = self.mod_center + m
        self.main_ft.c += (new_c - self.main_ft.c) / 5.


    def intro_t(self):
        if self.scene_init:
            self.mod_center = BULB_2_CENTER
            self.angle = 10

            self.min_angle = -30
            self.max_angle = 75
            self.mod_radius = 0.2
            self.mod_scale = 0.15 / self.scene_length

        self.angle = self.angle + self.sign * 4 * self.high_speed
        s = self.mod_scale * self.scene_pos
        d = s + self.mod_radius - ((s + 0.12) * self.freqs[LOWF][0] * 1.5)
        m = cmath.rect(d, math.radians(self.angle))
        new_c = self.mod_center + m + complex(0, 0.1 * self.freqs[MIDF][0])
        self.main_ft.c += (new_c - self.main_ft.c) / 4.0

    def brk01(self):
        if self.scene_init:
            self.brk_zoom_length = self.scene_length + 96
            self.brk_zoom_start = self.scene_start
            self.mod_center = -0.485642857143+0.604142857143j
        new_c = self.linspace(self.main_ft.c, self.mod_center) + complex(0, 1 * self.freqs[MIDF][0])
        #while True:
        #    if self.solve(new_c):
        #        break
        #    new_c += 0.2j
        self.main_ft.c += (new_c - self.main_ft.c) / 4.0
        self.move_view(self.main_ft, radius = 0.8)
        self.move_view(self.debug_ft, center=BULB_3_VIEW, length = self.brk_zoom_length, pos = self.frame - self.brk_zoom_start)

    def bass_th(self):
        if self.scene_init:
            self.mod_radius = 0.13
            self.mod_center = BULB_3_CENTER
            self.angle = 30
            self.min_angle = 30
            self.max_angle = 110
            if self.args.debugo:
                self.debug_ft.set_view(center=BULB_3_VIEW, radius=0.3)
        if not self.args.debugo:
            self.move_view(self.debug_ft, center=BULB_3_VIEW, length = self.brk_zoom_length, pos = self.frame - self.brk_zoom_start)
            self.move_view(self.debug_ft, radius=0.3, length = 96)

        self.angle = self.angle + self.sign * 1.9 * self.high_speed
        d_p = 0
        while True:
            d = d_p + self.mod_radius - (self.mod_radius * self.freqs[LOWF][0] * 1.2)
            m = cmath.rect(d, math.radians(self.angle))
            new_c = self.mod_center + m #+ complex(0., 0.33 * self.freqs[MIDF][0])
            #if self.solve(new_c):
            #    break
            #d_p += 0.01
            break
        self.main_ft.c += (new_c - self.main_ft.c) / 4.0


        #self.bump_mod(-self.mod_radius, self.mod_radius)

    def brk02(self):
        if self.scene_init:
            self.mod_center = (-0.530133928571+0.668165178571j)
            self.c_path = np.linspace(self.main_ft.c, self.mod_center, self.scene_length)
            self.cos_win_scale = np.pi / 2. / self.scene_length
            self.hue_path = np.logspace(np.log10(self.main_ft.hue), np.log10(0.4), self.scene_length)
            self.max_iter_path = np.linspace(self.main_ft.max_iter, 128., self.scene_length)

        new_c = self.linspace(self.main_ft.c, self.mod_center) + complex(0.2 * self.mid_speed) * np.cos(self.scene_pos * self.cos_win_scale) + complex(0, -0.1*self.mid_speed) * np.cos(self.scene_pos * self.cos_win_scale)
        self.main_ft.c += (new_c - self.main_ft.c) / 5.
        self.move_view(self.debug_ft, center=self.mod_center, radius=0.008)
        self.move_view(self.main_ft, center=0j, radius=0.13)
        self.main_ft.hue = self.hue_path[self.scene_pos]
        self.main_ft.max_iter = float(int(self.max_iter_path[self.scene_pos]))

    def main_th(self):
        #self.move_view(self.debug_ft, radius=0.008, length=42)
        if self.scene_init:
            mc = self.mod_center + 0.002j
            s = 0.007
            self.m_path = Path((
                    mc-complex(0, s+0.001), mc - s, mc + complex(0, s+0.001), mc+s+0.002, mc-complex(0, s+0.001)
                ), self.scene_length * 2)
            self.c_path = self.m_path.logs() #sin(0.0004, cycles = 4)
            self.path_pos = 0

        # main_th
        self.path_pos += 8 * self.high_speed
        new_c = self.c_path[int(self.path_pos % (self.scene_length * 2))]
        new_c += (self.mod_center - new_c) * self.freqs[LOWF][0] * 1.4
        self.main_ft.c += (new_c - self.main_ft.c) / 5.0

    def brk03(self):
        if self.scene_init:
            self.cos_win_scale = np.pi / 2. / self.scene_length
            self.c_path = np.linspace(self.main_ft.c, (-0.562907929095+0.641504235883j), self.scene_length)
#            self.hue_path = np.linspace(self.main_ft.hue, 0.3, self.scene_length)
        self.move_view(self.debug_ft, center = (-0.562907929095+0.641504235883j), radius = 0.0410525522232)
        self.move_view(self.main_ft, center = 0j, radius = 0.368940544128)
        new_c = self.c_path[self.scene_pos] + complex(0, 0.05 * self.mid_speed) * np.cos(self.scene_pos * self.cos_win_scale)
        self.main_ft.c += (new_c - self.main_ft.c) / 4.
#        self.main_ft.hue = self.hue_path[self.scene_pos]


    def deep_th(self):
        # Allow negative d...
        if self.scene_init:
            self.mod_center = self.main_ft.c
            self.mod_radius = 0.013
            self.angle = 0
            self.scale = 0.01 / self.scene_length

        #  deep_th
        d = self.scale * (self.scene_length - self.scene_pos) + self.mod_radius * self.freqs[LOWF][0] * 8
        self.mod_radius -= self.scale
        self.angle = self.angle + (self.freqs[HIGHF][0])
        m = cmath.rect(d, math.radians(self.angle))
        new_c = self.mod_center + m - complex(0.01 * self.mid_speed)

        self.main_ft.c += (new_c - self.main_ft.c) / (5.0) * (0.1  + 1 * self.scene_pos / self.scene_length)
        self.move_view(self.main_ft, radius = 0.1)
        self.move_view(self.debug_ft, radius = 0.02)

    def brk04(self):
        if self.scene_init:
            self.mod_center = -0.62246875+0.4265625j
            self.cos_win_scale = np.pi / 2. / self.scene_length
            self.hue_path = np.logspace(np.log10(self.main_ft.hue), np.log10(0.5), self.scene_length)
            self.max_iter_path = np.linspace(self.main_ft.max_iter, 73., self.scene_length)
        self.move_view(self.main_ft, radius = 1.6875) #, length = self.scene_length / 2.)
        self.move_view(self.debug_ft, center = self.mod_center, length = self.scene_length / 3.)
        self.move_view(self.debug_ft, radius = 0.08125, length = self.scene_length / 4.)
        new_c = self.linspace(self.main_ft.c, (-0.605+0.44159375j)) + complex(0, -0.2 * self.freqs[LOWF][0]) * np.cos(self.scene_pos * self.cos_win_scale)
        self.main_ft.c += (new_c - self.main_ft.c) / 5.0
        self.main_ft.hue = self.hue_path[self.scene_pos]
        self.main_ft.max_iter = float(int(self.max_iter_path[self.scene_pos]))

    def end_th(self):
        if self.scene_init:
            self.min_r = 0.015
            self.max_r = 0.05
            self.mod_radius = 0.98
            self.angle = 40
            self.min_angle = 40
            self.max_angle = 146

        self.angle = self.angle + self.sign * self.high_speed
        d = self.max_r - (self.max_r - self.min_r) * self.freqs[LOWF][0]
        new_c = self.mod_center + cmath.rect(d, math.radians(self.angle % 360))
        self.main_ft.c += (new_c - self.main_ft.c) / (5.0) #* (0.1  + 1 * self.scene_pos / self.scene_length)
        self.move_view(self.main_ft, radius = 0.2)

    def ending(self):
        pass

    def fadeout(self):
        if self.scene_init:
            self.c_path = np.linspace(self.main_ft.c, -5+0j, self.scene_length)
        self.move_view(self.main_ft, center = 0j, radius = 3.0)
        self.move_view(self.debug_ft, center = 0j, radius = 3.5)
        self.main_ft.c = self.c_path[self.scene_pos]

    def render(self, debug_ft):
        self.pixels = np.roll(self.pixels, -1, axis=0)
        y_split = self.window_size[1] / len(self.draw_point)
        cur_pos = -1
        pos = 0
        self.pixels[cur_pos] *= 0
        for freq in self.draw_point:
            if pos:
                self.pixels[cur_pos][y_split * pos] = 0x4e4e4e
            f, s, c = freq
            self.pixels[cur_pos][-1 + (pos + 1 ) * y_split - y_split * f] = c
            if s:
                self.pixels[cur_pos][-1 + (pos + 1 ) * y_split - y_split * s] = ~c
            pos += 1

        for idx in xrange(len(self.c_values)):
            if idx >= self.c_num_draw:
                break
            point = self.c_values[idx]
            debug_ft.draw_complex(point, rgb(*[1 * (self.c_num_draw - 1 - idx) / float(self.c_num_draw)] * 3))

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--wav", required = True)
    parser.add_argument("--play", action="store_const", const=True)
    parser.add_argument("--encode", action="store_const", const=True)
    parser.add_argument("--bpm", type=float, default=105.)
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--scene")
    parser.add_argument("--scene_stop")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--stop", type=int, default=9001)
    parser.add_argument("--debugo", action="store_const", const=True)
    parser.add_argument("--debug", action="store_const", const=True)
    parser.add_argument("--single", action="store_const", const=True)
    parser.add_argument("--record", type=str)
    args = parser.parse_args()

    if args.encode and not args.record:
        print "You need to specify --record directory"
        exit(1)

    freq, wav = scipy.io.wavfile.read(args.wav)
    audio_frame_size = freq / args.fps
    # Inject intro black data
    wav_length = len(wav) / audio_frame_size
    wav = np.concatenate((np.zeros(shape=(audio_frame_size * FADEIN_LENGTH, 2), dtype='i2'), wav, np.zeros(shape=(audio_frame_size * FADEOUT_LENGTH, 2), dtype='i2')))
    audio_frames = np.linspace(0, len(wav), int(len(wav) / freq * args.fps), endpoint=False)
    spectrogram = SpectroGram(audio_frame_size)
    mod = Modulator((MOD_WIDTH, SG_HEIGHT), args.bpm, args.fps, wav_length, args)

    if args.scene:
        s = mod.scenes_name[args.scene]
        start_frame, end_frame = s[0] + args.start, s[0] + s[1]
        if args.stop != 9001:
            end_frame = s[0] + args.stop
        if args.scene_stop:
            s = mod.scenes_name[args.scene_stop]
            end_frame = s[0] + s[1]
    else:
        start_frame = args.start
        end_frame = min(len(audio_frames), args.stop + FADEIN_LENGTH)

    if args.play:
        pygame.mixer.init(frequency = freq, channels = len(wav[0]), buffer = audio_frame_size)

    screen = Screen(WINSIZE)
    waterfall = Waterfall((WINSIZE[0] - WAV_WIDTH - MOD_WIDTH, SG_HEIGHT), audio_frame_size)
    wavgraph = WavGraph((WAV_WIDTH, WINSIZE[1] - SG_HEIGHT), audio_frame_size)
    if args.debugo:
        args.debug = True

    if args.debug:
        screen.add(waterfall, (0, WINSIZE[1] - SG_HEIGHT))
        screen.add(mod,  (WINSIZE[0] - WAV_WIDTH - MOD_WIDTH, WINSIZE[1] - SG_HEIGHT))
        screen.add(wavgraph, (WINSIZE[0] - WAV_WIDTH, 0))
        if args.debugo:
            args.record = None
            debug_ft = Fractal((WINSIZE[0] - WAV_WIDTH, WINSIZE[1] - SG_HEIGHT), color_vector = dark_color_factory)
            main_ft  = Fractal((0, 0))
            screen.add(debug_ft)
            screen.add(main_ft, (WINSIZE[0] - WAV_WIDTH, WINSIZE[1] - SG_HEIGHT))
        else:
            debug_ft = Fractal((WAV_WIDTH, SG_HEIGHT), color_vector = dark_color_factory)
            main_ft = Fractal((WINSIZE[0] - WAV_WIDTH, WINSIZE[1] - SG_HEIGHT))
            screen.add(main_ft)
            screen.add(debug_ft, (WINSIZE[0] - WAV_WIDTH, WINSIZE[1] - SG_HEIGHT))
    else:
        debug_ft = Fractal((0, 0), color_vector = dark_color_factory)
        main_ft = Fractal(WINSIZE)
        screen.add(main_ft)

    debug_ft.max_iter = 69.

    if args.record:
        dname = args.record
        args.play = None
    else:
        dname = None

    clock = pygame.time.Clock()
    frame = 0
    last_fps = (-2, time.time())
    render_speed = -1
    last_render_speed = render_speed

    # Init
    while True:
        start_time = time.time()
        audio_buf = wav[audio_frames[frame]:audio_frames[frame]+audio_frame_size]
        spectrogram.transform(audio_buf)
        scene_name = mod.update(frame, spectrogram, main_ft, debug_ft)

        if frame >= start_frame:
            wavgraph.render(audio_buf)
            waterfall.render(spectrogram)
            debug_ft.render()
            if not args.debugo:
                main_ft.render()
            mod.render(debug_ft)
            screen.update()
            if main_ft.c.real >= 0: r_sign = "+"
            else:                r_sign = ""
            if main_ft.c.imag >= 0: i_sign = "+"
            else:                i_sign = ""
            c_str = "%s: z*z%s%.6f%s%.6fj" % (scene_name, r_sign, main_ft.c.real, i_sign, main_ft.c.imag)
            if not args.debugo and args.debug and WINSIZE[0] > 50:
                screen.draw_msg("[%04d] %s" % (frame, c_str))
            pygame.display.update()
            if dname:
                screen.capture(dname, frame)

            end_time = time.time()
            accomplished = 100. * (frame - start_frame) / (end_frame - start_frame)
            remaining = end_frame - frame
            status_line = "\r[%04d] %02d %% (remaining: %4d)" % (frame, accomplished, remaining)
            if (frame+1) % 5 == 0:
                if render_speed == -1:
                    render_speed = float(frame - start_frame) / (end_time - start_time)
                else:
                    render_speed = float(frame - last_fps[0]) / (end_time - last_fps[1])
                last_render_speed = render_speed
                last_fps = (frame, end_time)
            status_line += "\t(eta = %04.2f sec)" % (remaining / np.mean((last_render_speed, render_speed)))
            status_line += " %s" % c_str
            sys.stdout.write(status_line)
            sys.stdout.flush()
            elapsed = end_time - start_time
            if args.single:
                raw_input("Press enter to quit")
                exit()


        if frame == start_frame and args.play:
            sound = pygame.mixer.Sound(array = wav[audio_frames[start_frame]:])
            sound.play()

        frame += 1
        if frame >= end_frame:
            print
            if dname:
                fname = "out.webm"
                pygame.display.quit()
                wav = wav[audio_frames[start_frame]:]
                scipy.io.wavfile.write("%s/audio.wav" % dname, freq, wav)
                ffmpeg = " ".join([
                    "ffmpeg", "-y", "-framerate", "%d" % args.fps, "-start_number", "%d" % start_frame,
                    "-i", "%s/%%04d.png" % dname, "-i", "%s/audio.wav" % dname, "-c:v", "libvpx", "-threads", "4",
                    "-b:v", "5M", "-c:a", "libvorbis", "%s/%s" % (dname, fname)])
                mplayer = " ".join(["mplayer", "-zoom", "-vo", "x11", "-fs", "%s/%s" % (dname, fname)])
                print "%s && \\\n  %s" % (ffmpeg, mplayer)
                if args.encode:
                    os.system("%s &> /dev/null" % ffmpeg)
                    if "DISPLAY" in os.environ:
                        raw_input("Press enter to play...")
                        os.system("%s &> /dev/null" % mplayer)
            break

        for e in pygame.event.get():
            if  e.type == MOUSEBUTTONDOWN: print e.pos
            elif e.type == KEYDOWN and e.key == K_ESCAPE: exit(0)

        if frame >= start_frame:
            clock.tick(args.fps)


if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        print
        if pool:
            pool.terminate()
            pool.join()
        raise
