from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheFamiliarFormula(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # TITLE ZONE
        title = Tex(r"Why is a Circle's Area $\pi r^2$?", font_size=42).to_edge(UP, buff=0.5)
        self.add(title)

        # CENTER ZONE SETUP
        grid = NumberPlane(
            x_range=[-8, 8, 2],
            y_range=[-5, 5, 2],
        ).set_opacity(0.3)

        circle = Circle(radius=1.5, color=BLUE).move_to(LEFT * 2.5)
        radius_line = Line(circle.get_center(), circle.get_right(), color=WHITE)
        radius_label = MathTex(r"r", font_size=36).next_to(radius_line, DOWN, buff=0.15)
        radius_group = VGroup(radius_line, radius_label)

        # Define formula with parts for later highlighting
        formula = MathTex(r"A", r"=", r"\pi", r"r^2", font_size=36).next_to(circle, RIGHT, buff=1)

        with self.voiceover(text="You've probably known for a long time that the area of a circle is given by the formula pi times its radius squared.") as tracker:
            self.play(
                Succession(
                    # Create the visual elements together
                    AnimationGroup(FadeIn(grid), Create(circle), Create(radius_group)),
                    # The formula appears towards the end of the sentence
                    Wait(tracker.duration * 0.2),
                    FadeIn(formula, shift=UP)
                ),
                run_time=tracker.duration
            )

        with self.voiceover(text="But why is that true? Where does this specific combination of pi and r-squared come from?") as tracker:
            pi_part = formula[2]
            r_squared_part = formula[3]
            
            # Zoom in on the formula while highlighting the parts as they are mentioned.
            # The Succession with proportional Waits ensures the highlights sync with the audio.
            self.play(
                self.camera.frame.animate.scale(0.8).move_to(formula),
                Succession(
                    Wait(tracker.duration * 0.5), # Wait until "pi" is said
                    Indicate(pi_part, color=YELLOW, scale_factor=1.5),
                    Wait(tracker.duration * 0.2), # Wait until "r-squared" is said
                    Indicate(r_squared_part, color=YELLOW, scale_factor=1.5)
                ),
                run_time=tracker.duration
            )