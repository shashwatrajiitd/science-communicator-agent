from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class RealWorldPayoff(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Puck"))

        # Define the bell curve as per the shared object spec
        bell_curve_func = lambda x: np.exp(-(x**2) / 2) / np.sqrt(2 * np.pi)
        bell_curve = FunctionGraph(
            bell_curve_func,
            x_range=[-3.5, 3.5],
            color=TEAL
        ).scale(1.5) # Scale for better visibility in portrait mode
        bell_curve.move_to(ORIGIN)

        # Define and position the title, ensuring continuity
        title = Text("The Bell Curve", font_size=36, color=TEAL)
        title.to_edge(UP, buff=0.3)

        # Add the persistent background elements
        background = VGroup(bell_curve, title)
        self.add(background)

        # Create icons for real-world examples
        test_score_icon = VGroup(
            Rectangle(width=1.2, height=1.5, stroke_color=WHITE, fill_color=BLACK, fill_opacity=0.8),
            Text("A+", font_size=60, color=GREEN)
        )

        gear_icon = Text("⚙️", font_size=120, color=GREY)
        
        # Use Text instead of MathTex to avoid LaTeX dependency issues
        finance_icon = Text("$", font_size=120, color=GREEN)

        # Create a placeholder for transformations
        icon_placeholder = test_score_icon.copy().move_to(ORIGIN)
        gear_icon.move_to(icon_placeholder)
        finance_icon.move_to(icon_placeholder)

        # Beat 1: Show real-world examples
        with self.voiceover(text="This powerful idea helps us predict everything from test scores to tiny errors in manufacturing.") as tracker:
            # Use Succession to chain animations within the voiceover duration
            self.play(
                Succession(
                    FadeIn(icon_placeholder, scale=0.7),
                    Wait(tracker.duration * 0.3),
                    Transform(icon_placeholder, gear_icon),
                    Wait(tracker.duration * 0.3),
                    Transform(icon_placeholder, finance_icon),
                    Wait(tracker.duration * 0.1) # Leave it on screen for a moment
                ),
                run_time=tracker.duration
            )

        # Beat 2: Conclude on the pattern's elegance
        with self.voiceover(text="It's the hidden pattern that brings order to the chaos of daily life.") as tracker:
            self.play(
                FadeOut(icon_placeholder),
                run_time=tracker.duration
            )