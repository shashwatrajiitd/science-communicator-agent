from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class PrimeNumberMystery(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Charon"))

        # Beat 1: Introduce numbers 1-20
        with self.voiceover(text="Prime numbers are the atoms of arithmetic, the building blocks for all other numbers.") as tracker:
            # Using Text to avoid latex dependency issues
            numbers = VGroup(*[Text(str(i), font_size=48) for i in range(1, 21)])
            numbers.arrange_in_grid(rows=5, cols=4, buff=0.75)
            numbers.scale_to_fit_width(self.camera.frame_width * 0.9)
            self.play(Write(numbers), run_time=tracker.duration)

        # Beat 2: Highlight primes, fade non-primes
        with self.voiceover(text="But they appear to follow no simple pattern, cropping up with no obvious rhyme or reason.") as tracker:
            primes = {2, 3, 5, 7, 11, 13, 17, 19}
            prime_mobjects = VGroup()
            non_prime_mobjects = VGroup()

            for i, num_mob in enumerate(numbers):
                num = i + 1
                if num in primes:
                    prime_mobjects.add(num_mob)
                else:
                    non_prime_mobjects.add(num_mob)

            self.play(
                prime_mobjects.animate.set_color(YELLOW),
                non_prime_mobjects.animate.set_color(GREY),
                run_time=tracker.duration
            )

        # Beat 3: Is there a hidden order?
        with self.voiceover(text="Is there a hidden order to their chaos?") as tracker:
            # Using Text to avoid latex dependency issues
            question_mark = Text("?", font_size=288).move_to(ORIGIN)
            
            primes_to_animate = VGroup(*prime_mobjects)

            self.play(
                FadeOut(non_prime_mobjects),
                primes_to_animate.animate.scale(0.7).move_to(ORIGIN),
                run_time=tracker.duration * 0.6
            )
            self.play(
                FadeIn(question_mark, scale=1.5),
                run_time=tracker.duration * 0.4
            )
