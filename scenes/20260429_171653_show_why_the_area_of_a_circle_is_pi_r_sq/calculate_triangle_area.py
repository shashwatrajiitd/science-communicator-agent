from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class CalculateTriangleArea(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Define constants based on shared object specs
        r = 2.0
        base_length = 2 * PI * r  # approx 12.566
        height_length = r

        # Define layout zones
        center_zone = LEFT * 3.5
        formula_zone = RIGHT * 3.5

        # Create triangle based on the 'unrolled_triangle' spec
        triangle_verts = [
            [0, 0, 0],
            [base_length, 0, 0],
            [0, height_length, 0]
        ]
        unrolled_triangle = Polygon(*triangle_verts, color=GREEN, fill_opacity=0.0, stroke_width=3)
        unrolled_triangle.scale_to_fit_width(7).move_to(center_zone)

        with self.voiceover(text="The area of all these strips is the same as the area of our original circle. And we can find the area of this triangle easily.") as tracker:
            self.play(
                DrawBorderThenFill(unrolled_triangle),
                run_time=tracker.duration
            )

        with self.voiceover(text="The base of the triangle is the circumference of the outermost ring, which is 2πr.") as tracker:
            verts = unrolled_triangle.get_vertices()
            base_line = Line(verts[0], verts[1], color=YELLOW, stroke_width=6)
            base_label = MathTex(r"2\pi r", font_size=36).next_to(base_line, DOWN, buff=0.3)
            base_group = VGroup(base_line, base_label)
            
            self.play(
                Create(base_line),
                Write(base_label),
                run_time=tracker.duration * 0.8
            )
            self.play(Indicate(base_group, scale_factor=1.1), run_time=tracker.duration * 0.2)

        with self.voiceover(text="The height of the triangle is simply the distance from the outermost ring to the center, which is the circle's radius, r.") as tracker:
            verts = unrolled_triangle.get_vertices()
            height_line = Line(verts[0], verts[2], color=WHITE, stroke_width=6)
            height_label = MathTex(r"r", font_size=36).next_to(height_line, LEFT, buff=0.3)
            height_group = VGroup(height_line, height_label)
            
            self.play(
                Create(height_line),
                Write(height_label),
                run_time=tracker.duration * 0.8
            )
            self.play(Indicate(height_group, scale_factor=1.1), run_time=tracker.duration * 0.2)

        with self.voiceover(text="The area of a triangle is one-half base times height. Plugging in our values, we get one-half of 2πr, times r.") as tracker:
            formula1 = MathTex(r"\text{Area} = \frac{1}{2} \cdot \text{base} \cdot \text{height}", font_size=36).move_to(formula_zone)
            self.play(Write(formula1), run_time=tracker.duration * 0.5)
            
            formula2 = MathTex(r"\text{Area} = \frac{1}{2} \cdot (2\pi r) \cdot r", font_size=36).move_to(formula_zone)
            self.play(TransformMatchingTex(formula1, formula2), run_time=tracker.duration * 0.5)

        with self.voiceover(text="The one-half and the two cancel out, leaving us with... pi times r squared. The area of the circle.") as tracker:
            formula_parts = MathTex(
                r"\text{Area}", r"=", r"\frac{1}{2}", r"\cdot", r"2", r"\pi r", r"\cdot", r"r", 
                font_size=36
            ).move_to(formula_zone)
            
            self.play(FadeTransform(formula2, formula_parts), run_time=tracker.duration * 0.3)
            
            half_part = formula_parts[2]
            two_part = formula_parts[4]
            cross1 = Cross(half_part, stroke_color=RED, stroke_width=4)
            cross2 = Cross(two_part, stroke_color=RED, stroke_width=4)
            self.play(Create(cross1), Create(cross2), run_time=tracker.duration * 0.3)
            
            final_formula = MathTex(r"\text{Area} = \pi r^2", font_size=42, color=YELLOW).move_to(formula_zone)
            
            remaining_mobjects = VGroup(
                formula_parts[0], formula_parts[1], # Area =
                formula_parts[5], # pi r
                formula_parts[6], # dot
                formula_parts[7]  # r
            )
            
            fade_out_mobjects = VGroup(
                cross1, cross2,
                formula_parts[2], # 1/2
                formula_parts[3], # dot
                formula_parts[4]  # 2
            )

            self.play(
                FadeOut(fade_out_mobjects),
                ReplacementTransform(remaining_mobjects, final_formula),
                run_time=tracker.duration * 0.4
            )
            
            self.play(Indicate(final_formula, scale_factor=1.2))