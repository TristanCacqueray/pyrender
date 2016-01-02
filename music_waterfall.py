#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0

# This is a basic Julia set explorer
from utils import *

#constants
FPS = 25

def main(argv):
    if len(argv) < 2:
        print "usage: %s audio.wav [start_frame]" % argv[0]
        return

    wav, audio_frame_size, audio_frames_path = load_wav(argv[1], fps = FPS)
    screen = Screen(WINSIZE)

    spectrogram = SpectroGram(audio_frame_size)
    waterfall = Waterfall((WINSIZE[0] * 5 / 6., WINSIZE[1]), audio_frame_size)
    wavgraph = WavGraph((WINSIZE[0] / 6, WINSIZE[1]), audio_frame_size)

    screen.add(waterfall, (0, 0))
    screen.add(wavgraph, (WINSIZE[0] * 5/6., 0))

    frame = 0
    if len(argv) == 3:
        frame = int(argv[2])
    sound = pygame.mixer.Sound(array = wav[audio_frames_path[frame]:])
    sound.play()
    pause = False
    clock = pygame.time.Clock()
    while True:
        start_time = time.time()
        if not pause:
            audio_buf = wav[audio_frames_path[frame]:audio_frames_path[frame]+audio_frame_size]
            spectrogram.transform(audio_buf)

            # Waterfall
            wavgraph.render(audio_buf)
            waterfall.render(spectrogram)

        screen.update()
        pygame.display.update()
        for e in pygame.event.get():
            if e.type not in (KEYDOWN, MOUSEBUTTONDOWN):
                continue
            if e.type == MOUSEBUTTONDOWN:
                print "Freq:", WINSIZE[1] - e.pos[1]
            else:
                if e.key == K_SPACE:
                    pause = not pause
                    if pause:
                        pygame.mixer.pause()
                    else:
                        pygame.mixer.unpause()
                if e.key == K_ESCAPE:
                    exit(0)
        end_time = time.time()
        elapsed = end_time - start_time
        if elapsed > 1 / (FPS * 1.2):
            print "Getting slow... %s" % elapsed
        clock.tick(FPS)
        if not pause:
            frame += 1

if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        pass
