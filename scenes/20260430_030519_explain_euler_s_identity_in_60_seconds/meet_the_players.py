from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class MeetThePlayers(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Initial state from the previous scene
        title = Text("Euler's Identity", font_size=42).to_edge(UP, buff=0.5)
        formula = MathTex(
            r"e", r"^{i", r"\pi}", r"+", r"1", r"=", r"0",
            font_size=72
        ).move_to(ORIGIN)
        
        # Color the constants yellow
        formula[0].set_color(YELLOW) # e
        formula[1].set_color(YELLOW) # i
        formula[2].set_color(YELLOW) # pi
        formula[4].set_color(YELLOW) # 1
        formula[6].set_color(YELLOW) # 0
        self.add(title, formula)

        # Beat 1: Introduce 'e'
        with self.voiceover(text="To understand it, let's meet the players. 'e' is the base of natural growth, roughly 2.718.") as tracker:
            e_symbol = MathTex(r"e", font_size=72)
            e_value = MathTex(r"= 2.718...", font_size=36).next_to(e_symbol, RIGHT, buff=0.3)
            e_group = VGroup(e_symbol, e_value).move_to(ORIGIN)
            
            self.play(
                FadeOut(title),
                FadeOut(formula),
                FadeIn(e_group, shift=DOWN),
                run_time=tracker.duration
            )

        # Beat 2: Introduce 'pi'
        with self.voiceover(text="'pi' comes from circles, representing the ratio of circumference to diameter, about 3.141.") as tracker:
            # Pi visualization
            circle = Circle(radius=1.2, color=BLUE)
            diameter = Line(circle.get_left(), circle.get_right(), color=YELLOW, stroke_width=6)
            
            # Labels
            diameter_label = Text("diameter", font_size=28).next_to(diameter, DOWN, buff=0.2)
            circumference_label = Text("circumference", font_size=28).next_to(circle, UP, buff=0.2)
            
            circle_group = VGroup(circle, diameter, diameter_label, circumference_label).move_to(LEFT * 3.5)

            # Pi text
            pi_symbol = MathTex(r"\pi", font_size=72)
            pi_value = MathTex(r"\approx 3.141...", font_size=36).next_to(pi_symbol, DOWN, buff=0.4)
            pi_text_group = VGroup(pi_symbol, pi_value).move_to(RIGHT * 3.5)
            
            pi_group = VGroup(circle_group, pi_text_group)

            self.play(
                FadeOut(e_group, shift=LEFT),
                FadeIn(pi_group, shift=RIGHT),
                run_time=tracker.duration
            )

        # Beat 3: Introduce 'i'
        with self.voiceover(text="And 'i' is the imaginary unit, a number defined as the square root of negative one.") as tracker:
            i_symbol = MathTex(r"i", font_size=72)
            i_definition = MathTex(r"i^2 = -1", font_size=36).next_to(i_symbol, RIGHT, buff=0.3)
            i_group = VGroup(i_symbol, i_definition).move_to(ORIGIN)
            
            self.play(
                FadeOut(pi_group),
                FadeIn(i_group, shift=UP),
                run_time=tracker.duration
            )