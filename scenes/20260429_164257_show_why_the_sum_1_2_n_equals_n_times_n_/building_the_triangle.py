from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class BuildingTheTriangle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # TITLE ZONE
        title = Text("A Visual Proof for the Sum of Integers", font_size=42).to_edge(UP, buff=0.5)

        # CENTER ZONE
        sum_100 = MathTex(r"1 + 2 + 3 + \dots + 100 = ?", font_size=36)

        with self.voiceover(text="How would you add up all the numbers from one to, say, one hundred? There's a wonderfully simple formula for this kind of problem.") as tracker:
            self.play(
                Write(title),
                Write(sum_100),
                run_time=tracker.duration
            )

        dot_row_1 = VGroup(Dot(radius=0.1, color=BLUE)).center()

        with self.voiceover(text="For any number 'n', the sum from 1 to n can be visualized. Let's represent each number in the sum with a row of dots.") as tracker:
            sum_n = MathTex(r"1 + 2 + 3 + \dots + n", font_size=36).move_to(sum_100)
            
            self.play(
                TransformMatchingTex(sum_100, sum_n),
                run_time=tracker.duration * 0.5
            )
            # After the transform, sum_100 now looks like sum_n. We fade out the original mobject.
            self.play(
                FadeOut(sum_100, shift=UP),
                FadeIn(dot_row_1, shift=DOWN),
                run_time=tracker.duration * 0.5
            )

        # This VGroup will hold all the dot rows and represent the triangle
        triangle_dots = VGroup()

        with self.voiceover(text="We add a row of two dots for the number two, three dots for three, and so on, all the way up to a final row of 'n' dots.") as tracker:
            n_visual = 6
            dot_radius = 0.1
            dot_spacing = 0.25

            # Create the full triangle as a target for the animation
            for i in range(1, n_visual + 1):
                row = VGroup(*[Dot(radius=dot_radius, color=BLUE) for _ in range(i)])
                row.arrange(RIGHT, buff=dot_spacing)
                triangle_dots.add(row)
            
            triangle_dots.arrange(DOWN, buff=dot_spacing, aligned_edge=LEFT)
            triangle_dots.center().shift(UP * 0.25)

            rows_to_add = VGroup(*triangle_dots[1:])
            
            self.play(
                # The single dot from the previous step transforms into the first row
                Transform(dot_row_1, triangle_dots[0]),
                # The remaining rows fade in sequentially
                LaggedStart(*[FadeIn(row, shift=DOWN * 0.2) for row in rows_to_add], lag_ratio=0.5),
                run_time=tracker.duration
            )

        with self.voiceover(text="This creates a neat triangular shape of dots. Notice that it's 'n' units high and 'n' units wide at its base.") as tracker:
            # Brace for height, applied to the entire triangle VGroup
            brace_height = Brace(triangle_dots, LEFT, buff=0.2)
            label_height = brace_height.get_tex("n", font_size=36)
            
            # Brace for the base, applied to the last row of the triangle
            brace_base = Brace(triangle_dots[-1], DOWN, buff=0.2)
            label_base = brace_base.get_tex("n", font_size=36)
            
            self.play(
                LaggedStart(
                    Create(brace_height),
                    Write(label_height),
                    Create(brace_base),
                    Write(label_base),
                    lag_ratio=0.25
                ),
                run_time=tracker.duration
            )

        self.wait(1)