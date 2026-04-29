from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheCriticalLineHypothesisCTheHypothesisStated(MovingCameraScene, VoiceoverScene):
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
        x_label = complex_plane.get_x_axis_label(Text("Real", font_size=24))
        y_label = complex_plane.get_y_axis_label(Text("Imaginary", font_size=24).rotate(PI/2), direction=LEFT, buff=0.3)
        plane_group = VGroup(complex_plane, x_label, y_label)

        strip_width = complex_plane.c2p(1, 0)[0] - complex_plane.c2p(0, 0)[0]
        critical_strip = Rectangle(
            width=strip_width,
            height=complex_plane.get_y_length(),
            stroke_width=0,
            fill_color=YELLOW,
            fill_opacity=0.3
        ).move_to(complex_plane.c2p(0.5, 0))

        q_mark = Text("?", font_size=42, color=WHITE).move_to(critical_strip.get_center())

        # Set initial camera state to match end of previous scene
        self.camera.frame.set_height(8.0 / 2.5)
        self.camera.frame.move_to(critical_strip.get_center())
        
        self.add(plane_group, critical_strip, q_mark)

        # --- Beat 1 ---
        with self.voiceover(text="Mathematicians have checked trillions of zeros, and the pattern holds. This is the Riemann Hypothesis.") as tracker:
            critical_line = Line(
                complex_plane.c2p(0.5, -30),
                complex_plane.c2p(0.5, 30),
                color=YELLOW,
                stroke_width=5
            )
            line_label = MathTex(r"x = \frac{1}{2}", font_size=28, color=YELLOW)
            line_label.next_to(complex_plane.c2p(0.5, 25), RIGHT, buff=0.2)
            
            zero_coords = [
                (0.5, 14.13), (0.5, -14.13), 
                (0.5, 21.02), (0.5, -21.02), 
                (0.5, 25.01), (0.5, -25.01),
                (0.5, 28.9), (0.5, -28.9) # Add a couple more for visual effect
            ]
            non_trivial_zeros = VGroup(*[
                Dot(complex_plane.c2p(x, y), color=TEAL, radius=0.06) for x, y in zero_coords
            ])

            title = Text("The Riemann Hypothesis:", font_size=32, weight=BOLD)
            statement = Text("All non-trivial zeros lie on\nthe critical line x = 1/2.", font_size=28, line_spacing=0.8)
            hypothesis_text = VGroup(title, statement).arrange(DOWN, buff=0.25, aligned_edge=LEFT)
            hypothesis_text.to_edge(DOWN, buff=0.5)

            self.play(
                self.camera.frame.animate.set_height(8.0).move_to(ORIGIN),
                FadeOut(q_mark),
                ReplacementTransform(critical_strip, critical_line),
                LaggedStart(*[GrowFromCenter(dot) for dot in non_trivial_zeros]),
                FadeIn(hypothesis_text),
                Write(line_label),
                run_time=tracker.duration
            )