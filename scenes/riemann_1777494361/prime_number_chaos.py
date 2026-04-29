from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class PrimeNumberChaos(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]

        # Using a grid of numbers to represent the number line in a portrait-friendly way.
        # This meets the spirit of "show a number line from 1 to 50" while being legible.
        numbers_vgroup = VGroup(*[
            Text(str(i), font_size=24) for i in range(1, 51)
        ]).arrange_in_grid(10, 5, buff=0.4)
        numbers_vgroup.scale_to_fit_height(6)
        numbers_vgroup.center()

        with self.voiceover(text="Prime numbers are the atoms of arithmetic, the building blocks for all other numbers.") as tracker:
            self.play(Write(numbers_vgroup), run_time=tracker.duration * 0.5)
            
            prime_mobjects = VGroup()
            for p in primes:
                # The grid is filled row by row, 5 numbers per row.
                # index = (row * cols) + col = ((p-1)//5 * 5) + (p-1)%5
                # But arrange_in_grid fills column by column by default.
                # index = (col * rows) + row = ((p-1)%5 * 10) + (p-1)//5
                # Let's just iterate and find them.
                prime_mobjects.add(numbers_vgroup[p-1])

            self.play(
                LaggedStart(
                    *[m.animate.set_color(YELLOW) for m in prime_mobjects],
                    lag_ratio=0.1
                ),
                run_time=tracker.duration * 0.5
            )

        with self.voiceover(text="But they seem to appear randomly. The gaps between them are chaotic and unpredictable.") as tracker:
            self.play(
                numbers_vgroup.animate.scale(0.85).to_edge(UP, buff=0.5),
                run_time=tracker.duration
            )

        with self.voiceover(text="But what if there is a hidden pattern? A secret music governing their locations?") as tracker:
            question_parts = VGroup(
                Text("Is there a pattern?", font_size=36),
            ).arrange(DOWN, buff=0.15).next_to(numbers_vgroup, DOWN, buff=1.0)

            self.play(
                FadeOut(numbers_vgroup, shift=UP),
                FadeIn(question_parts, shift=UP),
                run_time=tracker.duration
            )
        
        self.wait(1)