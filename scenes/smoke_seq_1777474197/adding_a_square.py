from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class AddingASquare(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Shared object from the previous scene, assumed to be at the center.
        blue_circle = Circle(radius=1.5, color=BLUE)
        self.add(blue_circle)
        
        square = Square(side_length=3.0, color=RED).move_to(3 * RIGHT)

        # Beat 1: Introduce the square
        with self.voiceover(text="Now, let's bring in another shape, the square.") as tracker:
            self.play(
                blue_circle.animate.move_to(3 * LEFT),
                FadeIn(square, shift=RIGHT),
                run_time=tracker.duration
            )

        # Pre-create mobjects for Beat 2 by constructing lines from vertices.
        # The vertex order for a Square is DL, DR, UR, UL.
        v = square.get_vertices()
        sides = VGroup(
            Line(v[0], v[1], color=RED), # Bottom
            Line(v[1], v[2], color=RED), # Right
            Line(v[2], v[3], color=RED), # Top
            Line(v[3], v[0], color=RED)  # Left
        )
        
        # Use Text instead of MathTex to avoid LaTeX dependency issues.
        side_labels = VGroup(
            Text("s", font_size=36).next_to(sides[0], DOWN, buff=0.2), # Bottom
            Text("s", font_size=36).next_to(sides[1], RIGHT, buff=0.2),# Right
            Text("s", font_size=36).next_to(sides[2], UP, buff=0.2),   # Top
            Text("s", font_size=36).next_to(sides[3], LEFT, buff=0.2)  # Left
        )

        # Beat 2: Highlight the sides
        with self.voiceover(text="Unlike the smooth curve of a circle, a square is made of four straight sides of equal length.") as tracker:
            # The Indicate animation will flash the lines we created, which perfectly overlap the square.
            self.play(
                Succession(
                    AnimationGroup(Indicate(sides[0], color=YELLOW), Write(side_labels[0])),
                    AnimationGroup(Indicate(sides[1], color=YELLOW), Write(side_labels[1])),
                    AnimationGroup(Indicate(sides[2], color=YELLOW), Write(side_labels[2])),
                    AnimationGroup(Indicate(sides[3], color=YELLOW), Write(side_labels[3])),
                ),
                run_time=tracker.duration
            )
        
        # Pre-create mobjects for Beat 3
        # Corners are formed by adjacent sides.
        angles = VGroup(
            RightAngle(sides[1], sides[0], length=0.4, color=WHITE), # Bottom-right
            RightAngle(sides[2], sides[1], length=0.4, color=WHITE), # Top-right
            RightAngle(sides[3], sides[2], length=0.4, color=WHITE), # Top-left
            RightAngle(sides[0], sides[3], length=0.4, color=WHITE)  # Bottom-left
        )

        # Beat 3: Highlight the angles
        with self.voiceover(text="And these sides meet at four perfect right angles.") as tracker:
            # Animate in a clockwise order for visual appeal.
            self.play(
                Succession(
                    Create(angles[2]), # Top-left
                    Create(angles[1]), # Top-right
                    Create(angles[0]), # Bottom-right
                    Create(angles[3]), # Bottom-left
                ),
                run_time=tracker.duration
            )