from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheGaussianMystery(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Zones
        center_zone = ORIGIN
        caption_zone = DOWN * 3

        # Beat 1: Introduce the Gaussian
        with self.voiceover(text="This is the famous bell curve, also known as the Gaussian function. It shows up everywhere, from statistics to physics.") as tracker:
            axes = Axes(
                x_range=[-4, 4, 1],
                y_range=[0, 1.2, 0.5],
                x_length=4.0,
                y_length=3.0,
                axis_config={"color": GREY},
            ).move_to(center_zone)
            
            x_label = axes.get_x_axis_label("x", edge=RIGHT, direction=RIGHT, buff=0.2)
            y_label = axes.get_y_axis_label("y", edge=UP, direction=UP, buff=0.2)
            
            gaussian_curve_1d = axes.plot(
                lambda x: np.exp(-x**2),
                x_range=[-4, 4],
                color=BLUE
            )
            
            self.play(
                Create(axes),
                Write(x_label),
                Write(y_label),
                run_time=tracker.duration * 0.5
            )
            self.play(
                Create(gaussian_curve_1d),
                run_time=tracker.duration * 0.5
            )
            self.wait(0.5)

        # Beat 2: Show the formula and integral
        with self.voiceover(text="Its formula is deceptively simple: e to the power of negative x squared. But if you ask, 'what's the total area under this curve?'...") as tracker:
            formula_simple = MathTex(r"y = e^{-x^2}", font_size=36).next_to(axes, UP, buff=0.3)
            
            integral_I = MathTex(r"I = \int_{-\infty}^{\infty} e^{-x^2} dx", font_size=36).move_to(caption_zone)
            
            area = axes.get_area(gaussian_curve_1d, x_range=[-4, 4], color=YELLOW, opacity=0.6)

            self.play(FadeIn(formula_simple), run_time=tracker.duration * 0.4)
            self.play(FadeOut(formula_simple, shift=UP), run_time=tracker.duration * 0.2)
            self.play(
                Create(area),
                Write(integral_I),
                run_time=tracker.duration * 0.4
            )

        # Beat 3: Reveal the answer with pi
        with self.voiceover(text="The answer is the square root of pi. Which is strange. Pi is the ratio of a circle's circumference to its diameter. What is it doing here?") as tracker:
            result = MathTex(r"I = \sqrt{\pi}", font_size=42).move_to(caption_zone)
            
            self.play(
                TransformMatchingTex(integral_I, result, transform_mismatched_size=True),
                run_time=tracker.duration * 0.7
            )
            
            question_mark = MathTex(r"?", font_size=48, color=YELLOW).next_to(result[0][2], UR, buff=0.05)
            
            self.play(
                FadeIn(question_mark, scale=0.5),
                run_time=tracker.duration * 0.3
            )
        
        self.wait(1)
