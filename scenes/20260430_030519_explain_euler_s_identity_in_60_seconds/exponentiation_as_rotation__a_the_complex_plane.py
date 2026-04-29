from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class ExponentiationAsRotationATheComplexPlane(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Initial state from the previous scene
        i_symbol = MathTex(r"i", font_size=72)
        i_definition = MathTex(r"i^2 = -1", font_size=36).next_to(i_symbol, RIGHT, buff=0.3)
        i_group = VGroup(i_symbol, i_definition).move_to(ORIGIN)
        self.add(i_group)

        # Beat 1: Introduce the complex plane
        with self.voiceover(text="The key is to see what happens on the complex plane, which has a real axis and an imaginary axis.") as tracker:
            # Create the complex plane based on the shared object spec
            axes = Axes(
                x_range=[-1.5, 1.5, 1],
                y_range=[-1.5, 1.5, 1],
                axis_config={"color": GREY, "include_tip": False},
                x_length=8,
                y_length=8,
            )
            # Add labels for the axes
            x_label = axes.get_x_axis_label(
                MathTex("Real", font_size=36), edge=RIGHT, direction=RIGHT, buff=0.4
            )
            y_label = axes.get_y_axis_label(
                MathTex("Imaginary", font_size=36), edge=UP, direction=UP, buff=0.4
            )
            
            complex_plane = VGroup(axes, x_label, y_label)

            self.play(
                FadeOut(i_group, shift=DOWN),
                Create(complex_plane),
                run_time=tracker.duration
            )
