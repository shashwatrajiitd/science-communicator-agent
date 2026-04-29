from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class AddingTheSquare(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Initialize objects from the previous scene's state
        blue_circle = Circle(radius=1.5, color=BLUE).move_to(ORIGIN)
        circle_label = Text("Circle", font_size=28).next_to(blue_circle, DOWN, buff=0.5)
        self.add(blue_circle, circle_label)

        circle_group = VGroup(blue_circle, circle_label)

        with self.voiceover(text="Now, let's introduce another fundamental shape.") as tracker:
            self.play(
                circle_group.animate.move_to([-2.5, 0, 0]),
                run_time=tracker.duration
            )

        red_square = Square(side_length=3.0, color=RED).move_to([2.5, 0, 0])

        with self.voiceover(text="This is a square. It has four equal sides and four right angles.") as tracker:
            self.play(
                Create(red_square),
                run_time=tracker.duration
            )

        square_label = Text("Square", font_size=28).next_to(red_square, DOWN, buff=0.5)

        with self.voiceover(text="Together, these simple shapes form the building blocks for more complex designs.") as tracker:
            self.play(
                FadeIn(square_label, shift=UP),
                run_time=tracker.duration
            )
