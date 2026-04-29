from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheCriticalLineHypothesisBPlottingTheZeros(ThreeDScene, VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # --- Setup: Recreate final state of previous scene ---
        complex_plane = Axes(
            x_range=[-8, 2, 2],
            y_range=[-30, 30, 10],
            x_length=4.0,
            y_length=7.0,
            axis_config={"color": GREY, "include_tip": False}
        )

        strip_width = complex_plane.c2p(1, 0)[0] - complex_plane.c2p(0, 0)[0]
        critical_strip = Rectangle(
            width=strip_width,
            height=8.0, # Fill the portrait frame height
            stroke_width=0,
            fill_color="#B5A642", # Darker yellow to match prior scene
            fill_opacity=0.5,
        ).move_to(complex_plane.c2p(0.5, 0))

        q_mark = Text("?", font_size=42).move_to(critical_strip.get_center())

        # Only add objects visible at the end of the previous scene for continuity
        self.add(critical_strip, q_mark)
        
        self.set_camera_orientation(phi=0, theta=-PI / 2)
        
        self.camera.focal_distance /= 2.5
        self.camera.frame_center = critical_strip.get_center()

        # --- Beat 1 ---
        with self.voiceover(text="Not just close to the line. Exactly on it.") as tracker:
            critical_line = Line(
                complex_plane.c2p(0.5, -35),
                complex_plane.c2p(0.5, 35),
                color=YELLOW
            )
            line_label = MathTex(r"x = \frac{1}{2}", font_size=28, color=YELLOW)
            line_label.next_to(complex_plane.c2p(0.5, 0), RIGHT, buff=0.15)
            
            # Fade in the complex plane for context as the strip transforms
            self.play(
                FadeIn(complex_plane),
                FadeOut(q_mark),
                FadeTransform(critical_strip, VGroup(critical_line, line_label)),
                run_time=tracker.duration * 0.3
            )

            zero1_coord = (0.5, 14.13)
            zero1_dot = Dot(complex_plane.c2p(*zero1_coord), color=TEAL, radius=0.05)
            zero1_label = MathTex(r"\frac{1}{2} + 14.13i", font_size=28)
            zero1_label.next_to(zero1_dot, RIGHT, buff=0.15)

            self.move_camera(frame_center=zero1_dot.get_center(), run_time=tracker.duration * 0.3)
            
            self.play(
                GrowFromCenter(zero1_dot),
                Write(zero1_label),
                run_time=tracker.duration * 0.3
            )
            self.play(FadeOut(zero1_label), run_time=tracker.duration * 0.1)

        # --- Beat 2 ---
        with self.voiceover(text="As we search for more zeros, they keep appearing on that same line, one after another.") as tracker:
            zero2_coord = (0.5, 21.02)
            zero3_coord = (0.5, 25.01)
            zero2_dot = Dot(complex_plane.c2p(*zero2_coord), color=TEAL, radius=0.05)
            zero3_dot = Dot(complex_plane.c2p(*zero3_coord), color=TEAL, radius=0.05)
            
            zeros_to_add = VGroup(zero2_dot, zero3_dot)
            
            all_zeros_group = VGroup(
                Dot(complex_plane.c2p(0.5, 14.13)),
                zero2_dot.copy(),
                zero3_dot.copy()
            )

            self.move_camera(
                frame_center=all_zeros_group.get_center(),
                zoom=1.0,
                run_time=tracker.duration * 0.5
            )
            self.play(
                LaggedStart(
                    *[GrowFromCenter(dot) for dot in zeros_to_add],
                    lag_ratio=0.6
                ),
                run_time=tracker.duration * 0.5
            )