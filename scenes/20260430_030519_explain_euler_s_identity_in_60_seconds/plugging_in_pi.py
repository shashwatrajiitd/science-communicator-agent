from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class PluggingInPi(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # SHARED OBJECTS - Setup to match previous scene's end state
        # complex_plane
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

        # unit_circle
        radius_in_scene_units = np.linalg.norm(axes.c2p(1, 0) - axes.c2p(0, 0))
        unit_circle = Circle(radius=radius_in_scene_units, color=WHITE).move_to(axes.c2p(0, 0))

        # rotating_point and radius_line (start at x=0, which is point (1,0) for animation clarity)
        rotating_point = Dot(axes.c2p(1, 0), color=YELLOW, radius=0.05)
        radius_line = Line(axes.c2p(0, 0), axes.c2p(1, 0), color=YELLOW)
        
        # angle_arc and its label 'x' - matching prior scene's visual
        origin_angle_circle = Circle(radius=0.3, color=BLUE).move_to(axes.c2p(0,0))
        angle_label = MathTex(r"x", font_size=36, color=BLUE).move_to(axes.c2p(0,0))

        # Top formula - matching prior scene's visual
        formula = MathTex(r"e^{ix}", font_size=42).next_to(imaginary_label, UP, buff=0.2)

        # Display initial state
        self.add(complex_plane, unit_circle, radius_line, rotating_point, formula, origin_angle_circle, angle_label)
        
        # Beat 1
        with self.voiceover(text="So, what happens when we set x to be exactly pi?") as tracker:
            new_formula = MathTex(r"e^{i\pi}", font_size=42).move_to(formula.get_center())
            self.play(
                TransformMatchingTex(formula, new_formula),
                run_time=tracker.duration
            )
            formula = new_formula

        # Beat 2
        with self.voiceover(text="The point travels a distance of pi, which is exactly halfway around the circle.") as tracker:
            # The arc is the same geometry as the initial circle, just partial
            final_arc = Arc(
                radius=0.3,
                start_angle=0,
                angle=PI,
                color=BLUE
            ).move_to(axes.c2p(0,0))
            pi_label = MathTex(r"\pi", font_size=36, color=BLUE).move_to(angle_label.get_center())

            self.play(
                Rotate(VGroup(radius_line, rotating_point), angle=PI, about_point=axes.c2p(0, 0)),
                Transform(origin_angle_circle, final_arc), # Transform the circle into the arc
                Transform(angle_label, pi_label),
                run_time=tracker.duration
            )

        # Beat 3
        with self.voiceover(text="It lands squarely on negative one.") as tracker:
            final_point_pos = axes.c2p(-1, 0)
            neg_one_label = MathTex(r"-1", font_size=36).next_to(final_point_pos, LEFT, buff=0.25)
            
            self.play(
                Indicate(rotating_point, scale_factor=1.5),
                FadeIn(neg_one_label, shift=UP*0.5),
                run_time=tracker.duration
            )