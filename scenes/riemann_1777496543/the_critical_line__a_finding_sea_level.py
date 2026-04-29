from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheCriticalLineAFindingSeaLevel(ThreeDScene, VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Charon"))

        # Recreate the final state of the previous scene
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
            fill_color=TEAL
        ).set_style(stroke_width=0)
        
        x_label = axes.get_x_axis_label(Tex("Real Part", font_size=24))
        y_label = axes.get_y_axis_label(Tex("Imaginary Part", font_size=24), buff=0.4)
        
        landscape_group = VGroup(axes, surface, x_label, y_label)

        # Set initial camera and objects to match the end of the previous scene
        self.set_camera_orientation(phi=25 * DEGREES, theta=-90 * DEGREES)
        self.camera.set_zoom(1.1)
        self.camera.frame_center = axes.c2p(0.5, 0, 0)
        self.add(landscape_group)
        
        self.wait(0.25) # Establish the scene for continuity

        with self.voiceover(text="These points, where the function's value is zero, are called the 'zeros'.") as tracker:
            zero_plane = Surface(
                lambda u, v: axes.c2p(u, v, 0),
                u_range=[-3, 4],
                v_range=[-30, 30],
                resolution=(10, 10),
                fill_opacity=0.5,
                fill_color=BLUE,
            ).set_style(stroke_width=0)
            
            # Start from below and rise up
            zero_plane.move_to(axes.c2p(0.5, 0, -1))
            self.play(
                zero_plane.animate.move_to(axes.c2p(0.5, 0, 0)),
                run_time=tracker.duration
            )

        with self.voiceover(text="Let's see where the landscape intersects this zero-level plane.") as tracker:
            zero_y_vals = [14.13, 21.02, 25.01]
            # Create dots at the zero locations, slightly above the plane to avoid z-fighting
            zeros_dots_pos = VGroup(*[
                Dot3D(axes.c2p(0.5, y, 0.02), color=YELLOW, radius=0.08) for y in zero_y_vals
            ])
            zeros_dots_neg = VGroup(*[
                Dot3D(axes.c2p(0.5, -y, 0.02), color=YELLOW, radius=0.08) for y in zero_y_vals
            ])
            all_zeros = VGroup(zeros_dots_pos, zeros_dots_neg)

            self.play(
                zero_plane.animate.set_fill(opacity=0.8),
                Create(all_zeros),
                run_time=tracker.duration
            )