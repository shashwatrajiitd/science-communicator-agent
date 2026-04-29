from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheEquation(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        title = Text("Euler's Identity", font_size=42).to_edge(UP, buff=0.5)

        # The formula is broken into parts to allow for individual highlighting.
        formula = MathTex(
            r"e", r"^{i", r"\pi}", r"+", r"1", r"=", r"0",
            font_size=72
        ).move_to(ORIGIN)

        # Parts for the five fundamental constants
        e_part = formula[0]
        i_part = formula[1]
        pi_part = formula[2]
        one_part = formula[4]
        zero_part = formula[6]

        with self.voiceover(text="This is often called the most beautiful equation in mathematics: Euler's identity.") as tracker:
            self.play(
                Write(title),
                Write(formula),
                run_time=tracker.duration
            )

        with self.voiceover(text="It connects five of the most fundamental constants in a single, elegant statement.") as tracker:
            # This animation changes the color of each constant in sequence,
            # ensuring the highlight persists.
            self.play(
                Succession(
                    ApplyMethod(e_part.set_color, YELLOW),
                    ApplyMethod(i_part.set_color, YELLOW),
                    ApplyMethod(pi_part.set_color, YELLOW),
                    ApplyMethod(one_part.set_color, YELLOW),
                    ApplyMethod(zero_part.set_color, YELLOW),
                ),
                run_time=tracker.duration
            )
        
        self.wait(1)
