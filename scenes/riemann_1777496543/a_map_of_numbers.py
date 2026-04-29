from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class AMapOfNumbers(ThreeDScene, VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Charon"))

        # --- SETUP FROM PREVIOUS SCENE ---
        # Set camera for initial 2D view
        self.set_camera_orientation(phi=0, theta=-90 * DEGREES)
        
        primes_under_100 = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]
        line_100 = NumberLine(
            x_range=[0, 100, 10],
            length=4.0,
            include_numbers=True,
            font_size=18,
        ).move_to(ORIGIN)
        dots_100 = VGroup(*[
            Dot(point=line_100.n2p(p), color=YELLOW) for p in primes_under_100
        ])
        question_mark = MathTex("?", font_size=300, color=WHITE).move_to(ORIGIN).set_opacity(0.7)
        
        initial_group = VGroup(line_100, dots_100, question_mark)
        self.add(initial_group)
        
        # --- 3D SCENE SETUP ---
        def zeta_landscape_func(u, v):
            # A simplified, visually representative function for |ζ(s)|
            # Pole at s=1 (u=1, v=0)
            pole_val = 1 / (np.sqrt((u - 1)**2 + v**2) + 0.1)
            
            # Dips for non-trivial zeros on the critical line u=0.5
            zeros_factor = 1.0
            for y_val in [14.13, 21.02, 25.01]:
                zeros_factor *= (1 - 0.9 * np.exp(-((u - 0.5)**2 * 15 + (v - y_val)**2 * 15)))
                zeros_factor *= (1 - 0.9 * np.exp(-((u - 0.5)**2 * 15 + (v + y_val)**2 * 15)))
            
            val = pole_val * zeros_factor
            return np.clip(val, 0, 4)

        axes = ThreeDAxes(
            x_range=[-3, 4, 1],
            y_range=[-30, 30, 10],
            z_range=[0, 4, 1],
            x_length=4,
            y_length=4,
            z_length=2.5,
        )

        surface = Surface(
            lambda u, v: axes.c2p(u, v, zeta_landscape_func(u, v)),
            u_range=[-3, 4],
            v_range=[-30, 30],
            resolution=(75, 75),
            fill_opacity=0.8,
            fill_color=TEAL,
            checkerboard_colors=[TEAL, DARK_BLUE]
        ).set_style(stroke_width=0)
        
        x_label = axes.get_x_axis_label(Tex("Real Part", font_size=24))
        y_label = axes.get_y_axis_label(Tex("Imaginary Part", font_size=24), buff=0.4)
        
        landscape_group = VGroup(axes, surface, x_label, y_label)

        with self.voiceover(text="To find this pattern, mathematicians explore a strange, infinite landscape.") as tracker:
            self.play(FadeOut(initial_group), run_time=1.5)
            # Set camera to 3D view instantly
            self.move_camera(phi=75 * DEGREES, theta=-100 * DEGREES, zoom=0.9)
            remaining_time = max(0.1, tracker.duration - 1.5)
            self.play(Create(landscape_group), run_time=remaining_time)
            self.begin_ambient_camera_rotation(rate=0.07)

        with self.voiceover(text="This landscape is a map of the Riemann Zeta function, a tool that connects the world of smooth waves to the jagged world of primes.") as tracker:
            formula = MathTex(r"\zeta(s) = \sum_{n=1}^{\infty} \frac{1}{n^s}", font_size=36)
            formula_bg = BackgroundRectangle(formula, color=BLACK, fill_opacity=0.7, buff=0.1)
            formula_group = VGroup(formula_bg, formula)
            self.add_fixed_in_frame_mobjects(formula_group)
            formula_group.to_corner(UR, buff=0.5)
            
            self.play(FadeIn(formula_group, shift=DOWN), run_time=tracker.duration * 0.4)
            self.wait(tracker.duration * 0.3)
            self.play(FadeOut(formula_group, shift=UP), run_time=tracker.duration * 0.3)
            self.remove_fixed_in_frame_mobjects(formula_group)

        with self.voiceover(text="The secrets of the primes are hidden in this terrain, specifically at the points where the landscape dips down to sea level.") as tracker:
            self.stop_ambient_camera_rotation()
            self.move_camera(
                phi=25 * DEGREES,
                theta=-90 * DEGREES,
                zoom=1.1,
                frame_center=axes.c2p(0.5, 0, 0),
                run_time=tracker.duration
            )
            self.wait(0.5)