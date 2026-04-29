from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class IntroducingTheCircle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Beat 1: Draw the circle
        circle = Circle(radius=2, color=BLUE).move_to(ORIGIN)
        with self.voiceover(text="This is a circle, one of the most fundamental and perfect shapes in all of mathematics.") as tracker:
            self.play(Create(circle), run_time=tracker.duration)

        # Beat 2: Show the center
        center_dot = Dot(circle.get_center(), color=WHITE)
        with self.voiceover(text="Every circle has a special point right at its middle, which we call the center.") as tracker:
            self.play(FadeIn(center_dot), run_time=tracker.duration)

        # Beat 3: Draw the radius
        radius_line = Line(center_dot.get_center(), circle.get_top(), color=WHITE)
        with self.voiceover(text="The distance from this center to any point on the circle's edge is always exactly the same.") as tracker:
            self.play(Create(radius_line), run_time=tracker.duration)

        # Beat 4: Label the radius and sweep
        # Use Text instead of MathTex to avoid LaTeX dependency
        radius_label = Text("r", font_size=36).next_to(radius_line, RIGHT, buff=0.2)
        with self.voiceover(text="We call this constant distance the radius, and usually label it with the letter 'r'.") as tracker:
            # Split the duration for the label appearing and the line sweeping.
            write_duration = tracker.duration * 0.25
            rotate_duration = tracker.duration * 0.75
            
            self.play(Write(radius_label), run_time=write_duration)
            
            # Use an updater to keep the label next to the line as it rotates.
            radius_label.add_updater(lambda m: m.next_to(radius_line, RIGHT, buff=0.2))
            
            self.play(
                Rotate(
                    radius_line,
                    angle=2 * PI,
                    about_point=center_dot.get_center(),
                    rate_func=linear
                ),
                run_time=rotate_duration
            )
            radius_label.clear_updaters()

        # Beat 5: Final pulse
        with self.voiceover(text="This simple rule, a constant distance from a center, is what gives the circle its perfect, symmetrical form.") as tracker:
            # Split duration for fade out and pulse.
            fade_out_duration = tracker.duration * 0.5
            pulse_duration = tracker.duration * 0.5
            
            self.play(
                FadeOut(center_dot),
                FadeOut(radius_line),
                FadeOut(radius_label),
                run_time=fade_out_duration
            )
            self.play(Indicate(circle, scale_factor=1.1, color=YELLOW), run_time=pulse_duration)
