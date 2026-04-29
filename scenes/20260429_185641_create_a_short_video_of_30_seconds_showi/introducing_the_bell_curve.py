from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class IntroducingTheBellCurve(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Puck"))

        # Define layout zones and parameters for portrait mode
        center_pos = ORIGIN

        # --- Shared Object: data_histogram (BLUE) ---
        # Generate data that approximates a bell curve for the histogram
        np.random.seed(0)
        data = np.random.normal(loc=0, scale=1, size=500)
        hist_values, _ = np.histogram(data, bins=12, range=(-3, 3))
        
        # Per patch notes, ensure the color is explicitly BLUE for all bars.
        data_histogram = BarChart(
            values=hist_values.tolist(),
            bar_names=None,
            y_range=[0, max(hist_values) * 1.1, 20],
            x_length=config.frame_width - 1,
            y_length=3,
            bar_colors=[BLUE for _ in hist_values],
        ).move_to(center_pos)
        
        # Start with the histogram on screen
        self.add(data_histogram)

        # --- Shared Object: bell_curve (TEAL) ---
        # Define the standard normal distribution function
        def bell_curve_func(x):
            return np.exp(-x**2 / 2) / np.sqrt(2 * PI)

        # Create the curve using FunctionGraph, removing the dependency on Axes to avoid LaTeX errors.
        bell_curve = FunctionGraph(
            bell_curve_func,
            x_range=[-3.5, 3.5],
            color=TEAL
        )
        
        # Scale and position the curve to match the histogram for a smooth transform
        bell_curve.set(width=data_histogram.width)
        bell_curve.scale_to_fit_height(data_histogram.height * 1.1) # A little taller for a nice peak
        bell_curve.align_to(data_histogram, DOWN)

        # --- Beat 1: Introduce the Bell Curve ---
        text_beat1 = "This is the Normal Distribution, famously known as the Bell Curve."
        with self.voiceover(text=text_beat1) as tracker:
            curve_label = Text("The Bell Curve", font_size=36).next_to(bell_curve, UP, buff=0.4)
            
            self.play(
                Transform(data_histogram, bell_curve),
                FadeIn(curve_label, shift=UP),
                run_time=tracker.duration
            )
        
        # --- Beat 2: Explain properties (average and extremes) ---
        text_beat2 = "It shows that most results cluster right around the average, with fewer and fewer at the extremes."
        with self.voiceover(text=text_beat2) as tracker:
            # Highlight the average at the peak
            # Use c2p (coordinates to point) to find the peak on the curve's coordinate system
            peak_point = bell_curve.c2p(0, bell_curve_func(0))
            peak_dot = Dot(peak_point, color=YELLOW)
            average_label = Text("Average", font_size=28).next_to(peak_dot, UP, buff=0.2)

            # Shade the tails to show the extremes using Area.
            # The x_range for Area refers to the function's original x-axis.
            left_tail = Area(bell_curve, x_range=[-3.5, -1.5], color=ORANGE, opacity=0.5)
            right_tail = Area(bell_curve, x_range=[1.5, 3.5], color=ORANGE, opacity=0.5)
            tails = VGroup(left_tail, right_tail)

            # Animate these highlights in sequence to match the narration
            self.play(
                LaggedStart(
                    GrowFromCenter(peak_dot),
                    Write(average_label),
                    lag_ratio=0.5
                ),
                run_time=tracker.duration * 0.5
            )
            self.play(
                FadeIn(tails),
                run_time=tracker.duration * 0.5
            )