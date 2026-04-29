from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class ThePrimeMystery(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Charon"))

        title = Text("The Prime Mystery", font_size=42).to_edge(UP, buff=0.3)
        self.add(title)

        # Beat 1
        text_beat1 = "Prime numbers are the atoms of arithmetic, the building blocks for all other numbers."
        with self.voiceover(text=text_beat1) as tracker:
            primes = [2, 3, 5, 7, 11, 13, 17, 19]
            numbers = VGroup(*[
                Text(str(i), font_size=36).set_color(YELLOW if i in primes else WHITE)
                for i in range(1, 21)
            ])
            numbers.arrange_in_grid(rows=5, cols=4, buff=0.4)
            numbers.move_to(ORIGIN)

            self.play(
                FadeIn(numbers, lag_ratio=0.1),
                run_time=tracker.duration
            )

        # Beat 2
        text_beat2 = "But they appear without any obvious pattern, a chaotic sequence stretching to infinity."
        with self.voiceover(text=text_beat2) as tracker:
            line = NumberLine(
                x_range=[0, 20, 5],
                length=4,
                include_tip=True,
                font_size=24,
            ).move_to(ORIGIN)

            prime_dots = VGroup(*[
                Dot(point=line.n2p(p), color=YELLOW)
                for p in [2, 3, 5, 7, 11, 13, 17, 19]
            ])

            self.play(
                FadeOut(numbers),
                Create(line),
                run_time=tracker.duration * 0.5
            )
            self.play(
                LaggedStart(*[FadeIn(dot, scale=1.5) for dot in prime_dots], lag_ratio=0.2),
                run_time=tracker.duration * 0.5
            )

        # Beat 3
        text_beat3 = "Or is there a secret music hidden within this chaos? A deep pattern governing them all?"
        with self.voiceover(text=text_beat3) as tracker:
            question_text = Text("Is there a pattern?", font_size=36).move_to(ORIGIN)

            self.play(
                FadeOut(VGroup(line, prime_dots)),
                FadeIn(question_text, shift=UP),
                run_time=tracker.duration
            )

        self.wait(1)
