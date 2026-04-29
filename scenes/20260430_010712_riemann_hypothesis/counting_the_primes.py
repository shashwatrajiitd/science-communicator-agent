from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class CountingThePrimes(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Charon"))

        # Set up the initial state from the previous scene to match the provided image
        positions = {
            "2": UP * 2.0 + LEFT * 0.8,
            "3": UP * 2.0 + RIGHT * 0.8,
            "5": LEFT * 1.8 + UP * 0.5,
            "7": RIGHT * 1.8 + UP * 0.5,
            "11": RIGHT * 1.8 + DOWN * 0.8,
            "13": LEFT * 1.8 + DOWN * 0.8,
            "17": LEFT * 1.2 + DOWN * 2.0,
            "19": RIGHT * 1.2 + DOWN * 2.0,
        }
        initial_primes = VGroup()
        for p_str, pos in positions.items():
            initial_primes.add(Text(p_str, font_size=60, color=YELLOW).move_to(pos))
        
        initial_primes.scale(0.8).move_to(ORIGIN)

        question_mark = Text("?", font_size=288, color=WHITE).move_to(ORIGIN)
        initial_group = VGroup(initial_primes, question_mark)
        self.add(initial_group)

        # Beat 1
        with self.voiceover(text="One way to find a pattern is to count them. We can define a function, often called pi of x, that tells us how many primes there are up to any number x.") as tracker:
            title = Text("The Prime-Counting Function", font_size=36).to_edge(UP, buff=0.3)
            axes = Axes(
                x_range=[0, 20.1, 5],
                y_range=[0, 8.1, 2],
                x_length=self.camera.frame_width * 0.9,
                y_length=self.camera.frame_height * 0.5,
                axis_config={"include_tip": False, "label_constructor": Text},
            ).next_to(title, DOWN, buff=0.5)
            
            x_label = axes.get_x_axis_label("x", edge=DR, direction=DR, buff=0.2)
            y_label = axes.get_y_axis_label(Text("π(x)"), edge=UL, direction=UL, buff=0.2)
            
            graph_setup = VGroup(title, axes, x_label, y_label)

            self.play(
                FadeOut(initial_group, shift=UP),
                FadeIn(graph_setup, shift=UP),
                run_time=tracker.duration
            )

        # Beat 2
        with self.voiceover(text="As we move along the number line, the count stays flat, and then jumps up by one every time we hit a prime.") as tracker:
            primes_up_to_20 = [2, 3, 5, 7, 11, 13, 17, 19]
            
            def prime_pi_20(x):
                return sum(1 for p in primes_up_to_20 if p <= x)

            prime_staircase = axes.plot(
                prime_pi_20,
                x_range=[0, 20, 0.01],
                discontinuities=primes_up_to_20,
                use_smoothing=False,
                color=BLUE
            )
            
            staircase_label = Text("π(x)", color=BLUE, font_size=36).next_to(
                axes.c2p(17, prime_pi_20(17)), UR, buff=0.1
            )

            self.play(
                Create(prime_staircase),
                Write(staircase_label),
                run_time=tracker.duration
            )

        # Beat 3
        with self.voiceover(text="This creates a jagged staircase. The central question is, can we predict the shape of these stairs?") as tracker:
            primes_up_to_50 = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]

            def prime_pi_50(x):
                return sum(1 for p in primes_up_to_50 if p <= x)

            new_axes = Axes(
                x_range=[0, 50.1, 10],
                y_range=[0, 15.1, 5],
                x_length=self.camera.frame_width * 0.9,
                y_length=self.camera.frame_height * 0.5,
                axis_config={"include_tip": False, "label_constructor": Text},
            ).move_to(axes.get_center())

            new_x_label = new_axes.get_x_axis_label("x", edge=DR, direction=DR, buff=0.2)
            new_y_label = new_axes.get_y_axis_label(Text("π(x)"), edge=UL, direction=UL, buff=0.2)

            new_prime_staircase = new_axes.plot(
                prime_pi_50,
                x_range=[0, 50, 0.01],
                discontinuities=primes_up_to_50,
                use_smoothing=False,
                color=BLUE
            )
            
            new_staircase_label = Text("π(x)", color=BLUE, font_size=36).next_to(
                new_axes.c2p(47, prime_pi_50(47)), UR, buff=0.1
            )

            self.play(
                Transform(axes, new_axes),
                Transform(prime_staircase, new_prime_staircase),
                Transform(x_label, new_x_label),
                Transform(y_label, new_y_label),
                Transform(staircase_label, new_staircase_label),
                run_time=tracker.duration
            )
