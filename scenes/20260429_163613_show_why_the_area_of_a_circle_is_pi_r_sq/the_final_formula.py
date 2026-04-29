from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
import numpy as np

class TheFinalFormula(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en", tld="com"))

        # Initial Setup
        r_val = 1.5
        triangle_base = 2 * PI * r_val
        triangle_height = r_val
        triangle = Polygon(
            [-triangle_base / 2, -triangle_height / 2, 0],
            [triangle_base / 2, -triangle_height / 2, 0],
            [0, triangle_height / 2, 0],
            color=BLUE,
            fill_opacity=0.6
        ).scale_to_fit_width(5)

        # Define the formula with parts separated for easier manipulation.
        # This single `formula` mobject will be transformed through the scene.
        formula = MathTex(
            r"A", r"=", r"\frac{1}{2}", r"\cdot", r"2", r"\pi", r"r", r"\cdot", r"r",
            font_size=36
        )

        scene_group = VGroup(triangle, formula).arrange(RIGHT, buff=1.5).move_to(ORIGIN)
        self.add(scene_group)

        with self.voiceover(text="Simplifying this expression, the one-half and the two cancel out...") as tracker:
            half = formula[2]
            two = formula[4]

            self.play(
                Circumscribe(half, color=YELLOW),
                Circumscribe(two, color=YELLOW),
                run_time=tracker.duration / 2
            )

            formula_mid_target = MathTex(
                r"A", r"=", r"\pi", r"r", r"\cdot", r"r",
                font_size=36
            ).move_to(formula, aligned_edge=LEFT)

            self.play(
                TransformMatchingTex(formula, formula_mid_target),
                run_time=tracker.duration / 2
            )

        with self.voiceover(text="...leaving us with pi times r times r, or pi r squared.") as tracker:
            formula_final_target = MathTex(
                r"A", r"=", r"\pi r^2",
                font_size=36
            ).move_to(formula, aligned_edge=LEFT)

            self.play(
                TransformMatchingTex(formula, formula_final_target),
                run_time=tracker.duration
            )

        with self.voiceover(text="And so, the area of this triangle, which is made from all the pieces of our circle, is exactly pi r squared.") as tracker:
            circle = Circle(radius=r_val, color=BLUE, fill_opacity=0.6).move_to(triangle)
            self.play(
                ReplacementTransform(triangle, circle),
                run_time=tracker.duration
            )

        with self.voiceover(text="A beautiful, visual proof for one of mathematics' most famous formulas.") as tracker:
            # The mobjects on screen are now `circle` and the transformed `formula`.
            final_group = VGroup(circle, formula)
            self.play(
                final_group.animate.arrange(RIGHT, buff=1).move_to(ORIGIN),
                run_time=tracker.duration
            )