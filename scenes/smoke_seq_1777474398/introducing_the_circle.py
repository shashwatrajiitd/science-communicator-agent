from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class IntroducingTheCircle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Shared object: blue_circle
        blue_circle = Circle(radius=1.5, color=BLUE)
        circle_label = Text("Circle", font_size=28).next_to(blue_circle, DOWN, buff=0.5)

        with self.voiceover(text="Here is a shape we see all the time.") as tracker:
            self.play(Create(blue_circle), run_time=tracker.duration)

        with self.voiceover(text="This is a circle, perfectly round.") as tracker:
            self.play(FadeIn(circle_label, shift=UP), run_time=tracker.duration)

        self.wait(1)
