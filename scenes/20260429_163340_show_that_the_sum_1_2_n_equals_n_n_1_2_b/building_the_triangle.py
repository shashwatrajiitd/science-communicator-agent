from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
import numpy as np

class BuildingTheTriangle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en", tld="com"))

        # Center zone will hold all visuals
        # Caption zone is not used in this scene

        with self.voiceover(text="What is the sum of the first one hundred integers? Or the first thousand? There's a beautiful way to find the answer without adding them one by one.") as tracker:
            sum_text = MathTex(r"1 + 2 + 3 + \dots + n = ?", font_size=42)
            self.play(Write(sum_text), run_time=tracker.duration)

        with self.voiceover(text="Let's visualize the problem. We can represent each number as a row of dots.") as tracker:
            self.play(FadeOut(sum_text), run_time=0.5)
            
            dot_rows = VGroup()
            animations = []
            n = 5
            for i in range(1, n + 1):
                row = VGroup(*[Dot(radius=0.12, color=BLUE) for _ in range(i)]).arrange(RIGHT, buff=0.25)
                if dot_rows:
                    row.next_to(dot_rows[-1], DOWN, buff=0.4)
                dot_rows.add(row)
                animations.append(FadeIn(row, shift=UP*0.2))
            
            dot_rows.center()
            self.play(AnimationGroup(*animations, lag_ratio=0.4), run_time=tracker.duration - 0.5)

        with self.voiceover(text="If we stack these rows, say for the numbers one through five, they form a neat triangular shape.") as tracker:
            self.play(
                dot_rows.animate.arrange(DOWN, buff=0.25, aligned_edge=LEFT).center(),
                run_time=tracker.duration
            )

        with self.voiceover(text="The total number of dots in this triangle is the sum we're looking for. In this case, it's the sum of the first five integers.") as tracker:
            sum_label = MathTex(r"1 + 2 + 3 + 4 + 5", font_size=36)
            sum_label.next_to(dot_rows, RIGHT, buff=0.5)

            n_label = MathTex(r"n=5", font_size=36)
            n_label.next_to(dot_rows, UP, buff=0.4)

            self.play(
                Indicate(dot_rows, color=YELLOW, scale_factor=1.1),
                Write(sum_label),
                FadeIn(n_label, shift=DOWN*0.2),
                run_time=tracker.duration
            )