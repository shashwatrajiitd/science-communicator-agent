from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class IntroduceFormula(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Define shared objects and other visuals
        the_circle = Circle(radius=2.0, color=BLUE).move_to(ORIGIN)
        radius_line = Line(the_circle.get_center(), the_circle.get_right(), color=WHITE)
        radius_label = MathTex(r"r").next_to(radius_line, DOWN, buff=0.15)

        # The formula will be our main caption
        formula = MathTex(r"A = \pi r^2", font_size=36)
        formula.to_edge(DOWN, buff=0.5)

        # Beat 1: Introduce the circle, radius, and formula
        with self.voiceover(text="You've probably learned that the area of a circle is given by the famous formula: pi times the radius squared.") as tracker:
            self.add(the_circle) # Per correctness check, circle is on screen from the start
            self.play(
                Create(radius_line),
                Write(radius_label),
                FadeIn(formula, shift=UP),
                run_time=tracker.duration
            )

        # Beat 2: Question the formula's origin
        with self.voiceover(text="But why this specific formula? Let's build an intuition for where this πr² actually comes from.") as tracker:
            self.play(
                Indicate(formula, scale_factor=1.2, color=YELLOW),
                run_time=tracker.duration
            )

        self.wait(1)