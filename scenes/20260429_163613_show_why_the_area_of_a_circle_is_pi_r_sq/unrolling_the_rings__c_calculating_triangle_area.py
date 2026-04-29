from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
import numpy as np

class UnrollingTheRingsCCalculatingTriangleArea(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en", tld="com"))

        # Setup: A right triangle representing the unrolled rings.
        # Base = 8 units, Height = 4 units.
        triangle_verts = [
            np.array([-4, -2, 0]),
            np.array([4, -2, 0]),
            np.array([-4, 2, 0])
        ]
        triangle = Polygon(*triangle_verts, color=BLUE, fill_opacity=0.5, stroke_width=6)
        triangle.move_to(ORIGIN)

        self.add(triangle)
        # Keep track of highlights and labels to fade them out later if needed,
        # but for this scene, we'll keep them.
        center_mobjects = VGroup(triangle)

        with self.voiceover(text="What are the dimensions of this new shape? The base is the length of the longest ring, our original circumference, 2 pi r.") as tracker:
            base_line = Line(triangle.get_vertices()[0], triangle.get_vertices()[1])
            base_highlight = base_line.copy().set_color(YELLOW).set_stroke(width=10)
            
            base_label = MathTex(r"2\pi r", font_size=36).next_to(base_line, DOWN, buff=0.4)
            
            self.play(
                Create(base_highlight),
                Write(base_label),
                run_time=tracker.duration
            )
            center_mobjects.add(base_highlight, base_label)

        with self.voiceover(text="And the height? That's just the thickness of all the rings stacked up, which is simply the circle's original radius, r.") as tracker:
            height_line = Line(triangle.get_vertices()[2], triangle.get_vertices()[0])
            height_highlight = height_line.copy().set_color(YELLOW).set_stroke(width=10)

            height_label = MathTex(r"r", font_size=36).next_to(height_line, LEFT, buff=0.4)
            
            self.play(
                Create(height_highlight),
                Write(height_label),
                run_time=tracker.duration
            )
            center_mobjects.add(height_highlight, height_label)

        with self.voiceover(text="The area of a triangle is one-half base times height. So, the area is one-half of 2 pi r, times r.") as tracker:
            # Split the voiceover duration for the two-part animation
            part1_duration = tracker.duration * 0.5
            part2_duration = tracker.duration * 0.5

            # Part 1: Show the general formula for a triangle's area
            formula1 = MathTex(r"\text{Area}", r" = \frac{1}{2} \times ", r"\text{base}", r" \times ", r"\text{height}", font_size=36)
            formula1.to_edge(DOWN, buff=0.5)
            self.play(Write(formula1), run_time=part1_duration)

            # Part 2: Substitute the base and height values
            formula2 = MathTex(r"\text{Area}", r" = \frac{1}{2} \times ", r"(2\pi r)", r" \times ", r"(r)", font_size=36)
            formula2.move_to(formula1.get_center())

            self.play(
                TransformMatchingTex(formula1, formula2),
                Indicate(base_label, scale_factor=1.2),
                Indicate(height_label, scale_factor=1.2),
                run_time=part2_duration
            )
        
        self.wait(1)