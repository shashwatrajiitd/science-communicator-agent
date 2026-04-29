from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheCriticalLineHypothesisADrawingTheLine(MovingCameraScene, VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # --- Setup: Recreate final state of previous scene ---
        # This setup ensures visual continuity from the previous scene.
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
            height=8.0, # Ensure it fills the portrait view
            stroke_width=0,
            fill_color=YELLOW,
            fill_opacity=0.3
        ).move_to(complex_plane.c2p(0.5, 0))

        q_mark = Text("?", font_size=42).move_to(critical_strip.get_center())

        # Set camera to match the end of the previous scene (zoomed in)
        self.camera.frame.move_to(critical_strip.get_center())
        self.camera.frame.set_width(config.frame_width / 2.5)
        
        self.add(complex_plane, critical_strip, q_mark)

        # --- Beat 1 ---
        with self.voiceover(text="In 1859, Bernhard Riemann made an astonishing guess.") as tracker:
            name_text = Text("Bernhard Riemann", font_size=36)
            year_text = Text("1859", font_size=32)
            caption_group = VGroup(name_text, year_text).arrange(DOWN, buff=0.2).move_to(self.camera.frame.get_center())

            self.play(
                FadeOut(q_mark, shift=UP),
                Write(caption_group),
                run_time=tracker.duration
            )
        
        self.play(FadeOut(caption_group))

        # --- Beat 2 ---
        with self.voiceover(text="He proposed that all of these mysterious zeros lie on a single, perfectly straight line.") as tracker:
            critical_line = Line(
                start=complex_plane.c2p(0.5, -40),
                end=complex_plane.c2p(0.5, 40),
                color=YELLOW,
                stroke_width=6.0
            )
            
            line_label = Text("Critical Line", font_size=28)
            # Position label relative to camera frame to ensure it's visible
            line_label.next_to(self.camera.frame.get_corner(DR), UL, buff=0.2)


            self.play(
                Create(critical_line),
                Write(line_label),
                run_time=tracker.duration
            )

        self.wait(1)