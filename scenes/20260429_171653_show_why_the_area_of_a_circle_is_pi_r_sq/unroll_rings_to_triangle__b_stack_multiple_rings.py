from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class UnrollRingsToTriangleBStackMultipleRings(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Constants based on shared objects and for visualization
        r = 2.0
        base_width = 2 * PI * r
        num_rings = 10
        dr = r / num_rings

        # Define layout positions
        circle_center = UP * 1.5 + LEFT * 4
        stack_anchor = DOWN * 3 + LEFT * (base_width / 2)

        # The circle from which rings are conceptually taken
        the_circle = Circle(radius=r, color=BLUE).move_to(circle_center)

        # The first, outermost strip, representing the state from the previous scene
        base_strip = Rectangle(
            width=base_width,
            height=dr,
            color=BLUE,
            fill_opacity=0.7,
            stroke_width=1.5
        ).move_to(stack_anchor, aligned_edge=DL)

        # A VGroup to manage the stack of unrolled strips
        stacked_strips = VGroup(base_strip)

        self.add(the_circle, base_strip)

        with self.voiceover(text="Now let's do the same for the next ring inside. It's slightly shorter, so its unrolled strip will be too.") as tracker:
            # Define the second ring and its corresponding strip
            r_1 = r - dr
            ring_1 = Annulus(
                inner_radius=r_1 - dr / 2,
                outer_radius=r_1 + dr / 2,
                color=BLUE,
                fill_opacity=0.7
            ).move_to(circle_center)

            strip_1 = Rectangle(
                width=2 * PI * r_1,
                height=dr,
                color=BLUE,
                fill_opacity=0.7,
                stroke_width=1.5
            ).next_to(base_strip, UP, buff=0, aligned_edge=LEFT)

            # Animate the ring appearing and transforming into the strip
            self.play(
                FadeIn(ring_1),
                run_time=0.5
            )
            self.play(
                Transform(ring_1, strip_1),
                run_time=tracker.duration - 0.5
            )
            stacked_strips.add(ring_1)

        with self.voiceover(text="If we keep doing this for every single ring, from the outside all the way to the center...") as tracker:
            remaining_rings = num_rings - 2
            if remaining_rings <= 0:
                self.wait(tracker.duration)
                return
                
            anim_duration_per_ring = tracker.duration / remaining_rings

            animations = []
            for i in range(2, num_rings):
                r_i = r - i * dr
                
                ring_i = Annulus(
                    inner_radius=r_i - dr / 2,
                    outer_radius=r_i + dr / 2,
                    color=BLUE,
                    fill_opacity=0.7
                ).move_to(circle_center)

                previous_strip = stacked_strips[-1]
                
                strip_i = Rectangle(
                    width=2 * PI * r_i,
                    height=dr,
                    color=BLUE,
                    fill_opacity=0.7,
                    stroke_width=1.5
                ).next_to(previous_strip, UP, buff=0, aligned_edge=LEFT)
                
                fade_in_time = min(0.1, anim_duration_per_ring * 0.1)
                transform_time = anim_duration_per_ring - fade_in_time

                animation = Succession(
                    FadeIn(ring_i, run_time=fade_in_time),
                    Transform(ring_i, strip_i, run_time=transform_time)
                )
                animations.append(animation)
                
                stacked_strips.add(ring_i)

            self.play(Succession(*animations))

        self.wait(1)