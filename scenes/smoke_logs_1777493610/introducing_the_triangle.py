from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class IntroducingTheTriangle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Per the brief, using vertices: (0, 2*sqrt(3)/3), (-2, -sqrt(3)/3), (2, -sqrt(3)/3)
        # This forms an isosceles triangle with base 4.
        v_top = np.array([0, 2 * np.sqrt(3) / 3, 0])
        v_left = np.array([-2, -np.sqrt(3) / 3, 0])
        v_right = np.array([2, -np.sqrt(3) / 3, 0])
        
        triangle = Polygon(v_top, v_left, v_right, color=WHITE)

        with self.voiceover(text="Here is a triangle.") as tracker:
            self.play(Create(triangle), run_time=tracker.duration)

        with self.voiceover(text="As you can see, it is a bright, cheerful yellow.") as tracker:
            self.play(triangle.animate.set_fill(YELLOW, opacity=1.0), run_time=tracker.duration)

        dots_and_labels = VGroup()

        with self.voiceover(text="A triangle is defined by three points, which we call vertices.") as tracker:
            dots = VGroup(
                Dot(v_top),
                Dot(v_left),
                Dot(v_right)
            ).set_color(WHITE)
            
            # Using Text instead of MathTex to avoid LaTeX dependency issues.
            label_A = Text("A").next_to(dots[0], UP, buff=0.2)
            label_B = Text("B").next_to(dots[1], LEFT, buff=0.2)
            label_C = Text("C").next_to(dots[2], RIGHT, buff=0.2)
            labels = VGroup(label_A, label_B, label_C)

            dots_and_labels.add(dots, labels)

            self.play(FadeIn(dots_and_labels), run_time=tracker.duration)

        with self.voiceover(text="And it has three straight sides connecting these vertices.") as tracker:
            # Create Line mobjects to represent the sides for the Indicate animation.
            side1 = Line(v_top, v_left)
            side2 = Line(v_left, v_right)
            side3 = Line(v_right, v_top)
            
            self.play(
                Succession(
                    Indicate(side1, color=WHITE),
                    Indicate(side2, color=WHITE),
                    Indicate(side3, color=WHITE),
                ),
                run_time=tracker.duration
            )

        with self.voiceover(text="This simple shape is one of the most fundamental in all of geometry.") as tracker:
            self.play(FadeOut(dots_and_labels), run_time=tracker.duration)
