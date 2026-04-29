from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class IntroducingTheCircle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Shared object definition
        blue_circle = Circle(radius=1.5, color=BLUE).move_to(ORIGIN)

        with self.voiceover(text="Let's begin with one of the most fundamental shapes in geometry: the circle.") as tracker:
            self.play(Create(blue_circle), run_time=tracker.duration)

        center_dot = Dot(blue_circle.get_center())
        # Start radius at 0 degrees (pointing right)
        radius_line = Line(blue_circle.get_center(), blue_circle.get_right(), color=WHITE)

        with self.voiceover(text="A circle is defined as the set of all points that are an equal distance from a single, central point.") as tracker:
            # Animate the appearance of the center and the initial radius line
            self.play(
                FadeIn(center_dot),
                Create(radius_line),
                run_time=tracker.duration / 2
            )
            # Animate the radius sweeping a full 360 degrees
            self.play(
                Rotate(radius_line, angle=2 * PI, about_point=blue_circle.get_center(), rate_func=linear),
                run_time=tracker.duration / 2
            )

        # After the sweep, the line is back at its original position.
        radius_label = Tex("radius", font_size=28).next_to(radius_line, UP, buff=0.15)

        # Create other radius lines to show they are all equal.
        other_radii = VGroup()
        angles = [PI / 3, 2 * PI / 3, PI, 5 * PI / 3]
        for angle in angles:
            other_radii.add(Line(blue_circle.get_center(), blue_circle.get_point_at_angle(angle), color=WHITE))

        with self.voiceover(text="This fixed distance is called the radius. Every point on the edge is exactly one radius away from the center.") as tracker:
            self.play(
                Write(radius_label),
                Create(other_radii),
                run_time=tracker.duration
            )
        
        self.wait(1)