from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
import numpy as np

class TheQuestion(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en", tld="com"))

        # Beat 1: Introduce the formula and circle with radius
        with self.voiceover(text="We all learn that the area of a circle is pi times its radius squared.") as tracker:
            # Center Zone: Circle and Radius
            circle = Circle(radius=1.5, color=BLUE).move_to(ORIGIN)
            radius_line = Line(circle.get_center(), circle.get_right(), color=WHITE)
            radius_label = MathTex(r"r", font_size=36).next_to(radius_line.get_center(), DOWN, buff=0.2)
            
            # Caption Zone: Formula
            formula = MathTex(r"A", r"=", r"\pi", r"r^2", font_size=36).to_edge(DOWN, buff=0.5)
            
            self.play(
                Create(circle),
                Create(radius_line),
                Write(radius_label),
                FadeIn(formula, shift=UP),
                run_time=tracker.duration
            )

        # Beat 2: Question why Pi is involved, showing C/D relationship
        with self.voiceover(text="But why this formula? Why does the special number pi also show up in its area?") as tracker:
            # Highlight pi in the formula
            self.play(
                Indicate(formula[2], color=YELLOW, scale_factor=1.5),
                run_time=tracker.duration * 0.4
            )

            # Define new elements for the pi definition diagram
            diameter = Line(circle.get_left(), circle.get_right(), color=WHITE)
            diameter_label = MathTex(r"D", font_size=36, color=WHITE).next_to(diameter, DOWN, buff=0.1)
            
            circumference_label_text = MathTex(r"C", font_size=36, color=WHITE).next_to(circle, UP, buff=0.2)
            circumference_arrow = CurvedArrow(
                circle.point_at_angle(PI/4),
                circle.point_at_angle(3*PI/4),
                angle=-PI/1.5,
                color=YELLOW
            )
            circumference_group = VGroup(circumference_label_text, circumference_arrow)
            
            pi_def = MathTex(r"\frac{C}{D} = \pi", font_size=36, color=WHITE).next_to(circle, RIGHT, buff=0.5)
            
            pi_diagram_elements = VGroup(diameter, diameter_label, circumference_group, pi_def)

            # Animate the transition cleanly: remove radius, add C and D elements
            self.play(
                FadeOut(radius_line, radius_label),
                FadeIn(pi_diagram_elements),
                run_time=tracker.duration * 0.6
            )

        # Beat 3: Prepare to dissect the circle
        with self.voiceover(text="Let's find an intuitive reason by dissecting the circle.") as tracker:
            # Clean up the screen, leaving only the main circle
            self.play(
                FadeOut(pi_diagram_elements),
                FadeOut(formula),
                run_time=tracker.duration * 0.5
            )
            
            # Glow the circle to prepare for the next scene
            self.play(
                Circumscribe(circle, color=YELLOW, time_width=2),
                run_time=tracker.duration * 0.5
            )