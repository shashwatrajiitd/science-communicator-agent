from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class IntroducingTheZetaFunction(ThreeDScene, VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Charon"))

        # Setup from previous scene to ensure continuity
        title = Text("The Prime Mystery", font_size=42).to_edge(UP, buff=0.3)
        question_text = Text("Is there a pattern?", font_size=36).move_to(ORIGIN)
        self.add(title, question_text)

        # Beat 1
        with self.voiceover(text="To find this pattern, we need a special tool: the Riemann Zeta function.") as tracker:
            # Using Text with unicode as a fallback for environments without LaTeX
            zeta_formula = Text("ζ(s) = Σ 1/(n^s)", font="Serif", font_size=36, color=WHITE)
            zeta_formula.move_to(ORIGIN)

            self.play(
                FadeOut(title),
                FadeOut(question_text),
                run_time=tracker.duration * 0.4
            )
            self.play(
                FadeIn(zeta_formula),
                run_time=tracker.duration * 0.3
            )
            self.play(
                Indicate(zeta_formula, scale_factor=1.2, color=YELLOW),
                run_time=tracker.duration * 0.3
            )

        # Beat 2
        with self.voiceover(text="Imagine this function as a vast, infinite landscape over a plane of numbers.") as tracker:
            self.play(
                zeta_formula.animate.scale(0.7).to_corner(UR, buff=0.3),
                run_time=tracker.duration * 0.2
            )

            axes = Axes(
                x_range=[-2, 3, 1],
                y_range=[-35, 35, 10],
                x_length=4,
                y_length=7,
                axis_config={"color": GREY},
                x_axis_config={"label_direction": DOWN, "include_tip": False, "font_size": 24},
                y_axis_config={"label_direction": LEFT, "include_tip": False, "font_size": 24},
            )
            x_label = axes.get_x_axis_label(Text("Real Part", font_size=24, color=GREY))
            y_label = axes.get_y_axis_label(Text("Imaginary Part", font_size=24, color=GREY).rotate(90 * DEGREES), edge=LEFT, direction=LEFT, buff=0.2)
            complex_plane = VGroup(axes, x_label, y_label)
            complex_plane.move_to(ORIGIN)

            def zeta_surface_func(u, v):
                pole = 2 * np.exp(-2 * ((u - 1)**2 + v**2))
                val = 1.0
                zero_coords = [14.13, 21.02]
                for y_val in zero_coords:
                    val -= 1.0 * np.exp(-0.5 * ((u - 0.5)**2 + (v - y_val)**2))
                    val -= 1.0 * np.exp(-0.5 * ((u - 0.5)**2 + (v + y_val)**2))
                val += 0.1 * np.sin(v/2)
                return np.maximum(0, val + pole)

            surface = Surface(
                lambda u, v: axes.c2p(u, v) + OUT * zeta_surface_func(u, v),
                u_range=[-2, 3],
                v_range=[-35, 35],
                resolution=(48, 96),
                fill_opacity=0.8,
            ).set_style(fill_color=BLUE, stroke_color=BLUE_E, stroke_width=0.5)

            self.set_camera_orientation(phi=75 * DEGREES, theta=-60 * DEGREES, zoom=0.8)
            
            self.play(
                Create(complex_plane),
                Create(surface),
                run_time=tracker.duration * 0.8
            )

        # Beat 3
        with self.voiceover(text="Certain points on this plane, when fed into the function, have an output of zero. These are the 'zeros', and they are the key.") as tracker:
            zero_coords_xy = [
                (0.5, 14.13), (0.5, -14.13),
                (0.5, 21.02), (0.5, -21.02)
            ]
            
            zero_dots_plane = VGroup(*[Dot(axes.c2p(x, y), color=YELLOW) for x, y in zero_coords_xy])
            zero_dots_surface = VGroup(*[Dot3D(axes.c2p(x, y), color=YELLOW) for x, y in zero_coords_xy])
            
            self.move_camera(
                phi=60 * DEGREES,
                theta=-45 * DEGREES,
                zoom=1,
                frame_center=axes.c2p(0.5, 0),
                run_time=tracker.duration * 0.5
            )

            self.play(
                LaggedStart(
                    *[GrowFromCenter(d) for d in zero_dots_plane],
                    *[GrowFromCenter(d) for d in zero_dots_surface],
                    lag_ratio=0.25
                ),
                run_time=tracker.duration * 0.5
            )