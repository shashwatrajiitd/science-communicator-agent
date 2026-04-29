from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheChaosOfPrimes(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Charon"))

        primes_under_100 = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]
        primes_under_30 = [p for p in primes_under_100 if p < 30]

        # --- Initial Setup for 0-30 view ---
        line_30 = NumberLine(
            x_range=[0, 30, 5],
            length=4.0, # Fit within the 4.5 frame width
            include_numbers=True,
            font_size=24,
        ).move_to(ORIGIN)

        dots_30 = VGroup(*[
            Dot(point=line_30.n2p(p), color=YELLOW) for p in primes_under_30
        ])
        initial_group = VGroup(line_30, dots_30)

        # Beat 1: Introduce primes up to 30
        with self.voiceover(text="The prime numbers are the atoms of arithmetic, the building blocks for all other numbers.") as tracker:
            self.play(
                Create(line_30),
                run_time=tracker.duration * 0.4
            )
            self.play(
                LaggedStart(*[FadeIn(dot, scale=1.5) for dot in dots_30], lag_ratio=0.1),
                run_time=tracker.duration * 0.6
            )

        # --- Setup for 0-100 view for transformation ---
        line_100 = NumberLine(
            x_range=[0, 100, 10],
            length=4.0, # Keep same length, so numbers get denser
            include_numbers=True,
            font_size=18, # Smaller font to fit
        ).move_to(ORIGIN)

        dots_100 = VGroup(*[
            Dot(point=line_100.n2p(p), color=YELLOW) for p in primes_under_100
        ])
        final_group = VGroup(line_100, dots_100)

        # Beat 2: Reveal the 'chaos' by transforming the line
        with self.voiceover(text="But they appear scattered along the number line without a clear pattern, a chaotic and unpredictable sequence.") as tracker:
            self.play(
                Transform(initial_group, final_group),
                run_time=tracker.duration
            )

        # Beat 3: Pose the central question
        with self.voiceover(text="Or is there a hidden order, a secret music governing their locations?") as tracker:
            question_mark = MathTex("?", font_size=300, color=WHITE)
            question_mark.move_to(ORIGIN)
            question_mark.set_opacity(0.7)
            self.play(
                FadeIn(question_mark, scale=0.5),
                run_time=tracker.duration
            )