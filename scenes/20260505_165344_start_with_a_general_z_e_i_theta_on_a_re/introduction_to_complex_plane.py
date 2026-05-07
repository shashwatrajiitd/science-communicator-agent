from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class IntroductionToComplexPlane(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Zones for portrait mode (9:16)
        title_zone = UP * 3.5
        center_zone = ORIGIN

        # Beat 1
        with self.voiceover(text="Many of us have seen Euler's famous formula, which connects exponents, imaginary numbers, and trigonometry.") as tracker:
            axes = Axes(
                x_range=[-1.5, 1.5, 1],
                y_range=[-1.5, 1.5, 1],
                x_length=4,
                y_length=4,
                axis_config={"color": GREY},
                x_axis_config={"numbers_to_include": [-1, 1]},
                y_axis_config={"numbers_to_include": [-1, 1]},
            ).move_to(center_zone)
            
            x_label = axes.get_x_axis_label(Tex("Real", font_size=28, color=GREY), edge=RIGHT, direction=RIGHT, buff=0.2)
            y_label = axes.get_y_axis_label(Tex("Imaginary", font_size=28, color=GREY), edge=UP, direction=UP, buff=0.2)
            origin_label = Tex("0", font_size=28, color=GREY).next_to(axes.c2p(0, 0), DR, buff=0.1)
            complex_plane = VGroup(axes, x_label, y_label, origin_label)

            formula = MathTex(r"z", r"=", r"e^{i", r"\theta", r"}", font_size=42).move_to(title_zone)

            self.play(
                Create(complex_plane),
                FadeIn(formula, shift=UP),
                run_time=tracker.duration
            )

        # Beat 2
        with self.voiceover(text="It tells us that for any angle theta, this expression gives us a point 'z' on a two-dimensional plane.") as tracker:
            theta_symbol = formula[3]
            z_symbol = formula[0]
            
            theta_val = PI / 4
            z_point_coord = axes.c2p(np.cos(theta_val), np.sin(theta_val))
            z_dot = Dot(point=z_point_coord, color=YELLOW)
            z_label = MathTex(r"z", font_size=36, color=YELLOW).next_to(z_dot, UR, buff=0.1)
            z_group = VGroup(z_dot, z_label)

            # Animate in sync with the narration. The `with` block will wait for the audio to finish.
            self.wait(2.5) # Approximate time until "theta" is spoken
            self.play(Indicate(theta_symbol, scale_factor=1.5), run_time=1.0)
            self.wait(0.5) # Approximate time until "'z'" is spoken
            self.play(Indicate(z_symbol, scale_factor=1.5), run_time=1.0)
            self.play(FadeIn(z_group, scale=0.5), run_time=1.0)


        # Beat 3
        with self.voiceover(text="But what happens as we let that angle change continuously? What shape are we actually tracing out?") as tracker:
            theta_symbol = formula[3]
            self.play(
                AnimationGroup(
                    Indicate(theta_symbol, color=YELLOW, scale_factor=1.7),
                    Flash(z_dot, color=ORANGE, flash_radius=0.4, line_length=0.2)
                ),
                run_time=tracker.duration
            )
