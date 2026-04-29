from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheTrivialZeros(ThreeDScene, VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # --- Setup: Recreate final state of previous scene ---
        def zeta_landscape_func(u, v):
            val = np.sin(u) + 0.5 * np.sin(v*2) + 0.3 * np.cos(u*v*0.5)
            return np.array([u, v, val])

        surface = Surface(
            zeta_landscape_func,
            u_range=[-4, 4], v_range=[-4, 4],
            resolution=(42, 42),
            fill_opacity=0.2,
        ).scale(1.5)
        surface.set_color_by_gradient(BLUE, TEAL, GREEN)

        old_plane_axes = Axes(
            x_range=[-4, 4, 1], y_range=[-4, 4, 1],
            x_length=4, y_length=4,
            axis_config={"color": GREY, "include_tip": False}
        )
        old_x_label = old_plane_axes.get_x_axis_label(Text("Real", font_size=24))
        old_y_label = old_plane_axes.get_y_axis_label(Text("Imaginary", font_size=24).rotate(PI/2), direction=LEFT, buff=0.3)
        old_plane = VGroup(old_plane_axes, old_x_label, old_y_label)

        old_zeros = VGroup(
            Dot(old_plane_axes.c2p(-PI/2, 0), color=ORANGE, radius=0.1),
            Dot(old_plane_axes.c2p(PI/2, PI), color=ORANGE, radius=0.1),
            Dot(old_plane_axes.c2p(-PI, PI/2), color=ORANGE, radius=0.1),
            Dot(old_plane_axes.c2p(0, -PI), color=ORANGE, radius=0.1)
        )
        
        self.set_camera_orientation(phi=70 * DEGREES, theta=-45 * DEGREES, zoom=0.9)
        self.add(surface, old_plane, old_zeros)

        # --- Beat 1 ---
        with self.voiceover(text="Some of these zeros are easy to find. They lie in a simple pattern on the negative number line.") as tracker:
            complex_plane = Axes(
                x_range=[-8, 2, 2],
                y_range=[-30, 30, 10],
                x_length=4.0,
                y_length=7.0,
                axis_config={"color": GREY, "include_tip": False}
            )
            x_label = complex_plane.get_x_axis_label(Text("Real", font_size=24))
            y_label = complex_plane.get_y_axis_label(Text("Imaginary", font_size=24).rotate(PI/2), direction=LEFT, buff=0.3)
            new_plane_group = VGroup(complex_plane, x_label, y_label)

            self.move_camera(phi=0, theta=-PI/2, frame_center=ORIGIN, run_time=tracker.duration * 0.3)
            self.play(
                FadeOut(surface, old_zeros),
                ReplacementTransform(old_plane, new_plane_group),
                run_time=tracker.duration * 0.3
            )
            
            trivial_zeros_dots = VGroup(
                Dot(complex_plane.c2p(-2, 0), color=ORANGE, radius=0.08),
                Dot(complex_plane.c2p(-4, 0), color=ORANGE, radius=0.08),
                Dot(complex_plane.c2p(-6, 0), color=ORANGE, radius=0.08),
            )
            label_l1 = Text("Trivial", font_size=28)
            label_l2 = Text("Zeros", font_size=28)
            trivial_zeros_label = VGroup(label_l1, label_l2).arrange(DOWN, buff=0.15)
            trivial_zeros_label.next_to(trivial_zeros_dots, DOWN, buff=0.3)

            self.play(
                LaggedStart(*[GrowFromCenter(dot) for dot in trivial_zeros_dots]),
                Write(trivial_zeros_label),
                run_time=tracker.duration * 0.4
            )

        # --- Beat 2 ---
        with self.voiceover(text="But there are other, infinitely more mysterious zeros hidden in a special region called the critical strip.") as tracker:
            strip_width = complex_plane.c2p(1, 0)[0] - complex_plane.c2p(0, 0)[0]
            critical_strip = Rectangle(
                width=strip_width,
                height=complex_plane.get_y_length(),
                stroke_width=0,
                fill_color=YELLOW,
                fill_opacity=0.3
            ).move_to(complex_plane.c2p(0.5, 0))

            q_mark = Text("?", font_size=42).move_to(critical_strip.get_center())

            self.play(
                FadeIn(critical_strip),
                Write(q_mark),
                run_time=tracker.duration
            )

        # --- Beat 3 ---
        with self.voiceover(text="The location of these 'non-trivial' zeros holds the key to understanding the primes.") as tracker:
            self.move_camera(
                frame_center=critical_strip.get_center(),
                zoom=2.5,
                run_time=tracker.duration
            )
