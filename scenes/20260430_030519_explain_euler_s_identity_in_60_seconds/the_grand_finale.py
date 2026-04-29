from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheGrandFinale(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Recreate the final state of the previous scene for continuity.
        axes = Axes(
            x_range=[-1.5, 1.5, 1],
            y_range=[-1.5, 1.5, 1],
            axis_config={"color": GREY},
            x_length=6,
            y_length=6,
        )
        x_ticks = VGroup(
            Text("-1", font_size=28).next_to(axes.c2p(-1, 0), DOWN, buff=0.15),
            Text("1", font_size=28).next_to(axes.c2p(1, 0), DOWN, buff=0.15),
        )
        y_ticks = VGroup(
            Text("-1", font_size=28).next_to(axes.c2p(0, -1), LEFT, buff=0.15),
            Text("1", font_size=28).next_to(axes.c2p(0, 1), LEFT, buff=0.15),
        )
        real_label = axes.get_x_axis_label("Real", edge=RIGHT, direction=RIGHT, buff=0.2)
        imaginary_label = axes.get_y_axis_label("Imaginary", edge=UP, direction=UP, buff=0.2)
        complex_plane = VGroup(axes, x_ticks, y_ticks, real_label, imaginary_label)

        radius_in_scene_units = np.linalg.norm(axes.c2p(1, 0) - axes.c2p(0, 0))
        unit_circle = Circle(radius=radius_in_scene_units, color=WHITE).move_to(axes.c2p(0, 0))

        # Point at -1
        final_point_pos = axes.c2p(-1, 0)
        rotating_point = Dot(final_point_pos, color=YELLOW, radius=0.05)
        radius_line = Line(axes.c2p(0, 0), final_point_pos, color=YELLOW)

        # Arc for pi
        final_arc = Arc(radius=0.3, start_angle=0, angle=PI, color=BLUE).move_to(axes.c2p(0,0))
        pi_label = MathTex(r"\pi", font_size=36, color=BLUE).move_to(axes.c2p(0, 0.5, 0))

        # Formula at top
        top_formula = MathTex(r"e^{i\pi}", font_size=42).next_to(imaginary_label, UP, buff=0.2)

        # Label for -1
        neg_one_label = MathTex(r"-1", font_size=36).next_to(final_point_pos, LEFT, buff=0.25)

        # Add all mobjects to the scene to match the prior frame.
        self.add(complex_plane, unit_circle, radius_line, rotating_point, final_arc, pi_label, top_formula, neg_one_label)
        self.wait(0.1) # Hold the initial frame for continuity

        with self.voiceover(text="And there we have it. e to the i pi equals negative one. A simple rearrangement gives us the famous identity.") as tracker:
            # Group background elements that will fade away.
            background_mobjects = VGroup(
                complex_plane, unit_circle, radius_line, rotating_point, final_arc, pi_label
            )

            # Define the target equations.
            initial_eq = MathTex(r"e^{i\pi}", r"=", r"-1", font_size=42).center()
            final_eq = MathTex(r"e^{i\pi}", r"+", r"1", r"=", r"0", font_size=42, color=WHITE).move_to(initial_eq)

            # Animation Part 1: Transform the on-screen elements into the first equation.
            self.play(
                FadeOut(background_mobjects),
                Transform(top_formula, initial_eq[0]),
                Transform(neg_one_label, initial_eq[2]),
                FadeIn(initial_eq[1]), # Fade in the '=' sign
                run_time=tracker.duration * 0.5
            )

            # Clean up the transformed parts and add the proper MathTex object for the next animation.
            self.remove(top_formula, neg_one_label)
            self.add(initial_eq)
            
            # Animation Part 2: Rearrange the equation.
            self.play(
                TransformMatchingTex(initial_eq, final_eq),
                run_time=tracker.duration * 0.5
            )
            
        self.wait(1)