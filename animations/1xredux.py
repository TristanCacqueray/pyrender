#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

from utils import *

#constants
WAV_WIDTH = int(WINSIZE[0] / 5)
MOD_WIDTH = int(WINSIZE[0] / 5)
SG_HEIGHT = int(WINSIZE[1] / 5)

FADEIN_LENGTH = 69
FADEOUT_LENGTH = 69

# Audio mod generator
class Fractal(ScreenPart, ComplexPlane):
    def __init__(self, window_size, c = None, color_vector = bright_color_factory):
        ScreenPart.__init__(self, window_size)
        self.c = c
        self.set_view(0j, 1)
        self.max_iter = 69.
        self.color_vector = np.vectorize(color_vector(self.max_iter))
        self.last_view = None

    def draw_complex(self, plane_coord, color = 0xffffff):
        coord = (int((plane_coord.real - self.offset[0]) * self.scale[0]),
                        self.window_size[1] - int((plane_coord.imag - self.offset[1]) * self.scale[1]))
        if coord[0] < 0 or coord[1] < 0 or coord[1] >= self.pixels.shape[1] or coord[0] >= self.pixels.shape[0]:
            return
        self.pixels[coord[0]][coord[1]] = color

    def render(self):
        if self.c is None:
            if (self.center, self.radius) == self.last_view:
                # Reuse pre-render
                self.pixels = self.pixels_copy.copy()
                return
            self.last_view = (self.center, self.radius)
        nparray = compute(complex_fractal, [self.window_size, self.offset, self.scale, self.max_iter, self.c, self.length])
        nparray = self.color_vector(nparray)
        self.pixels = nparray.reshape(*self.window_size)
        if self.c is None: # Keep mandelbrot render
            self.pixels_copy = self.pixels.copy()

BULB_2_CENTER=(-0.119357142857+0.739607142857j)

class Modulator(ScreenPart):
    def __init__(self, window_size, bpm, fps, end_frame):
        ScreenPart.__init__(self, window_size)
        self.freqs = [
            [0., (250, 403), 4., 0x008080],
            [0., (95, 127), 10., 0x808000],
            [0., (50, 59), 10., 0x808080],
            [0., (10, 15), 1., 0xff0000],
            [0., None, 1., 0xc1c1c1], # Speed
        ]
        self.c_values = []
        self.fps = fps
        self.scale = fps * 4 * 60 / bpm

        self.resting_point = 1.0
        self.speed = 0
        self.angle = 0

        self.scenes = [
            [end_frame, "fadeout"],
            [4457,      "ending"],
            [3542,      "end_th"],
            [3314,      "brk#04"],
            [2857,      "deep_th"],
            [2628,      "brk#03"],
            [1942,      "main_th"],
            [1828,      "brk#02"],
            [1371,      "bass_th"],
            [857,       "brk#01"],
            [228,       "intro_t"],
            [0,         "bells"],
            [-FADEIN_LENGTH, "fadein"],
        ]
        self.scenes_name = {}
        for idx in xrange(len(self.scenes)):
            scene = self.scenes[idx]
            scene[0] += FADEIN_LENGTH
            if idx == 0:
                scene_length = FADEOUT_LENGTH
            else:
                scene_length = self.scenes[idx - 1][0] - scene[0]
            scene.insert(1, scene_length)
            self.scenes_name[scene[-1]] = scene[:2]

    def update(self, frame, spectrogram, main_ft, debug_ft):
        # Update mods
        for freq in self.freqs:
            current, freq_range, decay, color = freq
            if not freq_range:
                continue
            vals = spectrogram.freq[freq_range[0]:freq_range[1]]
            if freq_range[1] - freq_range[0] > 25:
                val = np.max(vals)
            else:
                #val = np.mean(vals)
                val = np.median(vals)
            val = max(0, val)
            if val > current:
                freq[0] = val
            else:
                freq[0] -= (current - val) / decay
        self.speed = max(0, self.speed + (1 - self.speed) / 3. * self.freqs[0][0] - self.speed / 12.)
        self.freqs[-1][0] = self.speed

        # Find scene
        for idx in xrange(len(self.scenes)):
            if frame >= self.scenes[idx][0]:
                scene_start, scene_length, scene_name = self.scenes[idx]
                break
        if idx == len(self.scenes):
            print "could not find scene %d" % frame
            exit(1)

        if scene_name == "fadein":
            if frame == scene_start:
                main_ft.set_view(center = 0j, radius = 3.0)
                debug_ft.set_view(center = 0j, radius = 1.5)

                # Zoom in path for the next 2 scenes
                self.scene_r_path = np.linspace(main_ft.radius, 1.3, scene_length + self.scenes_name["intro_t"][1])

                self.scene_c_path = np.linspace(1+1.3j, (-0.1054+1.17262710083j), scene_length)

                self.debug_r_path = np.linspace(1.5, 0.3, scene_length)
                self.debug_v_path = np.linspace(0j, BULB_2_CENTER, scene_length)

            debug_ft.set_view(center = self.debug_v_path[frame-scene_start], radius = self.debug_r_path[frame-scene_start])
            main_ft.set_view(radius = self.scene_r_path[frame-scene_start])
            main_ft.c = self.scene_c_path[frame-scene_start]

        elif scene_name == "bells":
            if frame == scene_start:
                # Circle mod
                self.mod_center = BULB_2_CENTER
                self.mod_radius = 0.2
                self.speed = 0.0
                self.angle = 45
                self.min_angle = 45
                self.max_angle = 320
                self.sign = 1

            # Keep on zooming
            main_ft.set_view(radius = self.scene_r_path[frame])
            d = self.mod_radius #- self.mod_radius * self.freqs[-2][0]
            a = self.angle
            m = cmath.rect(d, math.radians(a))
            if self.angle >= self.max_angle:
                self.sign = -1
            elif self.angle < self.min_angle:
                self.sign = 1

            self.angle = self.angle + 1 #self.speed * 10 * self.sign

            main_ft.c = self.mod_center + m #- complex(0.05 * self.freqs[1][0]) - complex(0, 0.1 * self.freqs[2][0])



        self.c_values.insert(0, main_ft.c)

        return scene_name
        # Update scene
        if frame >= 9000:
            return

        elif frame >= 2857 + INTRO_LENGTH:
            scene_start, scene_len = 2857, 457
            if frame == scene_start:
                debug.set_view(center = -0.8, radius = 1.3)
                scene.set_view(radius = 2.0)
                self.mod_center = -0.3+0j
                self.mod_radius = 1.3 / 2.

            m = cmath.rect(self.mod_radius - 0.4 * self.freqs[-2][0], math.radians((frame*2) % 360)) # -5 * self.freqs[-3][0]))
            scene.c = self.mod_center + m - complex(0, 0.1 * self.freqs[2][0])
 
        elif frame >= 1942 + INTRO_LENGTH:
            scene_start, scene_len = 1942, 686
            if frame == scene_start:
                debug.set_view(center = -0.8, radius = 1.3)
                scene.set_view(radius = 2.0)
                self.mod_center = -0.3+0j
                self.mod_radius = debug.radius / 2.

            m = cmath.rect(self.mod_radius, math.radians(frame % 360)) # -5 * self.freqs[-2][0]))
            scene.c = self.mod_center + m

    def render(self, debug_ft):
        self.pixels = np.roll(self.pixels, -1, axis=0)
        y_split = self.window_size[1] / len(self.freqs)
        cur_pos = -1
        pos = 0
        self.pixels[cur_pos] *= 0
        for freq in self.freqs:
            if pos:
                self.pixels[cur_pos][y_split * pos] = 0x4e4e4e
            self.pixels[cur_pos][-1 + (pos + 1 ) * y_split - y_split * freq[0]] = freq[-1]
            pos += 1

        c_num_draw = 96
        for idx in xrange(len(self.c_values)):
            if idx >= c_num_draw:
                break
            point = self.c_values[idx]
            debug_ft.draw_complex(point, rgb(*[1 * (c_num_draw - 1 - idx) / float(c_num_draw)] * 3))

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--wav", required = True)
    parser.add_argument("--play", action="store_const", const=True)
    parser.add_argument("--single", action="store_const", const=True)
    parser.add_argument("--bpm", type=float, default=105.)
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--scene")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--stop", type=int, default=9001)
    parser.add_argument("--debug", action="store_const", const=True)
    parser.add_argument("--record", type=str)
    args = parser.parse_args()


    freq, wav = scipy.io.wavfile.read(args.wav)
    audio_frame_size = freq / args.fps
    # Inject intro black data
    wav_length = len(wav) / audio_frame_size
    wav = np.concatenate((np.zeros(shape=(audio_frame_size * FADEIN_LENGTH, 2), dtype='i2'), wav, np.zeros(shape=(audio_frame_size * FADEOUT_LENGTH, 2), dtype='i2')))
    audio_frames = np.linspace(0, len(wav), int(len(wav) / freq * args.fps), endpoint=False)
    spectrogram = SpectroGram(audio_frame_size)
    mod = Modulator((MOD_WIDTH, SG_HEIGHT), args.bpm, args.fps, wav_length)

    start_frame = args.start + FADEIN_LENGTH
    end_frame = min(len(audio_frames), args.stop + FADEIN_LENGTH)
    if args.scene:
        s = mod.scenes_name[args.scene]
        start_frame, end_frame = s[0], s[0] + s[1]

    if args.record:
        dname = "%s_%04d" % (args.record, start_frame)
        args.play = None
    else:
        dname = None

    if args.play:
        pygame.mixer.init(frequency = freq, channels = len(wav[0]), buffer = audio_frame_size)

    screen = Screen(WINSIZE)
    waterfall = Waterfall((WINSIZE[0] - WAV_WIDTH - MOD_WIDTH, SG_HEIGHT), audio_frame_size)
    wavgraph = WavGraph((WAV_WIDTH, WINSIZE[1] - SG_HEIGHT), audio_frame_size)
    if args.debug:
        debug_ft = Fractal((WINSIZE[0] - WAV_WIDTH, WINSIZE[1] - SG_HEIGHT), color_vector = dark_color_factory)
        main_ft  = Fractal((WAV_WIDTH, SG_HEIGHT))
        screen.add(debug_ft)
        screen.add(main_ft, (WINSIZE[0] - WAV_WIDTH, WINSIZE[1] - SG_HEIGHT))
        dname = None
    else:
        debug_ft = Fractal((WAV_WIDTH, SG_HEIGHT), color_vector = dark_color_factory)
        main_ft = Fractal((WINSIZE[0] - WAV_WIDTH, WINSIZE[1] - SG_HEIGHT))
        screen.add(main_ft)
        screen.add(debug_ft, (WINSIZE[0] - WAV_WIDTH, WINSIZE[1] - SG_HEIGHT))

    screen.add(waterfall, (0, WINSIZE[1] - SG_HEIGHT))
    screen.add(mod,  (WINSIZE[0] - WAV_WIDTH - MOD_WIDTH, WINSIZE[1] - SG_HEIGHT))
    screen.add(wavgraph, (WINSIZE[0] - WAV_WIDTH, 0))

    clock = pygame.time.Clock()
    frame = 0
    last_fps = (-2, time.time())
    render_speed = 1

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
            if not args.debug:
                main_ft.render()
            mod.render(debug_ft)
            screen.update()
            if main_ft.c.real >= 0: r_sign = "+"
            else:                r_sign = ""
            if main_ft.c.imag >= 0: i_sign = "+"
            else:                i_sign = ""
            c_str = "%s: z*z%s%.6f%s%.6fj" % (scene_name, r_sign, main_ft.c.real, i_sign, main_ft.c.imag)
            if not args.debug:
                screen.draw_msg("[%04d] %s" % (frame, c_str))
            pygame.display.update()
            if dname:
                screen.capture(dname, frame)

            end_time = time.time()
            accomplished = 100. * (frame - start_frame) / (end_frame - start_frame)
            remaining = end_frame - frame
            status_line = "\r%02d %% (remaining: %4d)" % (accomplished, remaining)
            if (frame+1) % 5 == 0:
                render_speed = float(frame - last_fps[0]) / (end_time - last_fps[1])
                last_fps = (frame, end_time)
            status_line += "\t(eta = %04.2f sec)" % (remaining / render_speed)
            status_line += " %s" % c_str
            sys.stdout.write(status_line)
            sys.stdout.flush()
            elapsed = end_time - start_time
            if args.single:
                return raw_input("press enter")

        if frame == start_frame and args.play:
            sound = pygame.mixer.Sound(array = wav[audio_frames[start_frame]:])
            sound.play()

        frame += 1
        if frame >= end_frame:
            print
            if dname:
                scipy.io.wavfile.write("%s/audio.wav" % dname, freq, wav[audio_frames[start_frame]:audio_frames[end_frame]])
                ffmpeg = " ".join([
                    "ffmpeg", "-y", "-framerate", "%d" % args.fps, "-start_number", "%d" % start_frame,
                    "-i", "%s/%%04d.png" % dname, "-i", "%s/audio.wav" % dname, "-c:v", "libvpx", "-threads", "4",
                    "-b:v", "5M", "-c:a", "libvorbis", "%s/out.webm" % dname])
                mplayer = " ".join(["mplayer", "-zoom", "-vo", "x11", "-fs", "%s/out.webm" % dname, "&>", "/dev/null"])
                print ffmpeg
                print os.system("%s &> /dev/null" % ffmpeg)
                print mplayer
                raw_input("Press enter to play...")
                print os.system("%s &> /dev/null" % mplayer)

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
