from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
import numpy as np

class CalculateTriangleArea(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en", tld="com"))

        # Define constants based on shared object specs
        r = 2.0
        base_length = 2 * PI * r  # approx 12.566
        height_length = r

        # Center Zone: The Triangle
        # Create triangle based on the shared object 'unrolled_triangle' spec
        triangle_verts = [ORIGIN, [base_length, 0, 0], [0, height_length, 0]]
        unrolled_triangle = Polygon(*triangle_verts, color=GREEN, fill_opacity=0.6, stroke_width=1)

        # Scale and position the triangle for the scene layout
        triangle_group = VGroup(unrolled_triangle).scale_to_fit_width(6).move_to(LEFT * 3.5 + DOWN * 0.5)

        # Beat 1: Introduce the triangle and its area.
        with self.voiceover(text="The area of all these strips is the same as the area of our original circle. And we can find the area of this triangle easily.") as tracker:
            self.play(FadeIn(triangle_group), run_time=tracker.duration * 0.5)
            flash = ShowPassingFlash(
                unrolled_triangle.copy().set_fill(GREEN, opacity=1.0).set_stroke(width=0),
                time_width=1.0,
            )
            self.play(flash, run_time=tracker.duration * 0.5)

        # Beat 2: Label the base.
        with self.voiceover(text="The base of the triangle is the circumference of the outermost ring, which is 2πr.") as tracker:
            # Get vertices from the scaled and positioned triangle
            verts = unrolled_triangle.get_vertices()
            base_line = Line(verts[0], verts[1], color=YELLOW, stroke_width=8)
            base_label = MathTex(r"2\pi r", font_size=36).next_to(base_line, DOWN, buff=0.3)
            
            self.play(
                Create(base_line),
                Write(base_label),
                run_time=tracker.duration * 0.7
            )
            self.play(Indicate(VGroup(base_line, base_label), scale_factor=1.1), run_time=tracker.duration * 0.3)

        # Beat 3: Label the height.
        with self.voiceover(text="The height of the triangle is simply the distance from the outermost ring to the center, which is the circle's radius, r.") as tracker:
            verts = unrolled_triangle.get_vertices()
            height_line = Line(verts[0], verts[2], color=WHITE, stroke_width=8)
            height_label = MathTex(r"r", font_size=36).next_to(height_line, LEFT, buff=0.3)
            
            self.play(
                Create(height_line),
                Write(height_label),
                run_time=tracker.duration * 0.7
            )
            self.play(Indicate(VGroup(height_line, height_label), scale_factor=1.1), run_time=tracker.duration * 0.3)

        # Beat 4: Introduce the triangle area formula and substitute.
        with self.voiceover(text="The area of a triangle is one-half base times height. Plugging in our values, we get one-half of 2πr, times r.") as tracker:
            formula_pos = RIGHT * 3
            formula1 = MathTex(r"\text{Area} = \frac{1}{2} \cdot \text{base} \cdot \text{height}", font_size=36).move_to(formula_pos)
            self.play(Write(formula1), run_time=tracker.duration * 0.5)
            
            formula2 = MathTex(r"\text{Area} = \frac{1}{2} \cdot (2\pi r) \cdot r", font_size=36).move_to(formula_pos)
            self.play(TransformMatchingTex(formula1, formula2, transform_mismatched_size=False), run_time=tracker.duration * 0.5)
            self.wait(0.1) # Small pause for readability

        # Beat 5: Simplify to get the final formula.
        with self.voiceover(text="The one-half and the two cancel out, leaving us with... pi times r squared. The area of the circle.") as tracker:
            # Create a version of the formula with parts for cancellation
            cancel_formula = MathTex(r"\text{Area} = ", r"\frac{1}{2}", r" \cdot (", r"2", r"\pi r) \cdot r", font_size=36).move_to(formula_pos)
            self.play(FadeTransform(formula2, cancel_formula), run_time=0.5)
            
            # Animate the cancellation
            half_part = cancel_formula[1]
            two_part = cancel_formula[3]
            cross1 = Cross(half_part, stroke_color=RED, stroke_width=4)
            cross2 = Cross(two_part, stroke_color=RED, stroke_width=4)
            self.play(Create(cross1), Create(cross2), run_time=tracker.duration * 0.4)
            
            # Transform to the final result
            final_formula = MathTex(r"\text{Area} = \pi r^2", font_size=42).move_to(formula_pos)
            
            # Group remaining parts for a clean transform
            remaining_parts = VGroup(
                cancel_formula[0], # "Area = "
                cancel_formula[4], # "pi r"
                cancel_formula[5]  # " \cdot r"
            )
            
            self.play(
                FadeOut(cross1, cross2, half_part, two_part, cancel_formula[2]),
                Transform(remaining_parts, final_formula),
                run_time=tracker.duration * 0.6
            )
            self.play(Indicate(final_formula, color=YELLOW, scale_factor=1.2))

        self.wait(1)