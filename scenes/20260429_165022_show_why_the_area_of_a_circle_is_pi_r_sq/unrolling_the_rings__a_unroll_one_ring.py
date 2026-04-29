from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class UnrollingTheRingsAUnrollOneRing(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # --- SCENE SETUP ---
        # Define ring parameters
        r_inner = 1.5
        r_outer = 1.65  # A bit thicker to be more visible
        r_avg = (r_inner + r_outer) / 2
        circumference = 2 * PI * r_avg

        # Create the ring, initially in the center
        ring = Annulus(
            inner_radius=r_inner,
            outer_radius=r_outer,
            color=BLUE,
            fill_opacity=0.7
        ).move_to(ORIGIN)

        # --- ANIMATIONS ---

        with self.voiceover(text="If we could snip this single ring and unroll it, it would straighten out into a line.") as tracker:
            # The target line for the transformation
            unrolled_line = Line(
                start=LEFT * circumference / 2,
                end=RIGHT * circumference / 2,
                color=BLUE,
                stroke_width=12  # Make it visually substantial
            ).move_to(ORIGIN)

            # Animate the ring appearing and moving up to isolate it
            self.play(FadeIn(ring), run_time=1.0)
            self.play(ring.animate.shift(UP * 2), run_time=1.0)

            # "Cut" animation at the top of the ring
            cut_point = ring.get_top()
            cut_mark = Line(
                start=cut_point,
                end=cut_point + DOWN * (r_outer - r_inner),
                color=RED,
                stroke_width=6
            )
            self.play(Create(cut_mark), run_time=0.5)
            self.play(FadeOut(cut_mark), run_time=0.5)

            # Animate the unrolling transformation
            self.play(Transform(ring, unrolled_line), run_time=tracker.duration - 3.0)

        with self.voiceover(text="The length of that line is simply the circumference of the ring it came from.") as tracker:
            # The 'ring' mobject has been transformed into the line
            unrolled_line = ring

            # Briefly show the original ring's ghost for context
            original_ring_ghost = Annulus(
                inner_radius=r_inner,
                outer_radius=r_outer,
                color=BLUE,
                fill_opacity=0.3
            ).move_to(unrolled_line.get_center() + UP * 2)

            # Create a brace and label for the line's length
            brace = Brace(unrolled_line, direction=DOWN, buff=0.4)
            label = MathTex(r"2\pi r", font_size=36).next_to(brace, DOWN, buff=0.2)
            
            # Split the animation to match the narration's flow
            t_fade_in_out = tracker.duration * 0.5
            t_label = tracker.duration * 0.5

            self.play(FadeIn(original_ring_ghost), run_time=t_fade_in_out / 2)
            self.play(
                GrowFromCenter(brace),
                Write(label),
                run_time=t_label
            )
            self.play(FadeOut(original_ring_ghost), run_time=t_fade_in_out / 2)

        self.wait(1)