from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class UnrollRingsToTriangleBStackMultipleRings(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Constants and layout
        r = 2.0
        num_rings_granularity = 20
        dr = r / num_rings_granularity
        circle_center = UP * 1.7

        # The circle from which rings are conceptually taken
        the_circle = Circle(radius=r, color=BLUE).move_to(circle_center)
        
        # The first, outermost strip, representing the state from the previous scene
        r_outermost = r - dr / 2
        base_width = 2 * PI * r_outermost
        base_strip = Rectangle(
            width=base_width,
            height=dr,
            color=BLUE,
            fill_opacity=0.7,
            stroke_width=1.5
        )
        # Position the stack's base, aligning to the left to form a right triangle
        base_strip.move_to(ORIGIN + DOWN * 1.5, aligned_edge=DL)
        
        stacked_strips = VGroup(base_strip)
        
        # Add initial objects to the scene
        self.add(the_circle, stacked_strips)
        self.wait(1)

        with self.voiceover(text="Now let's do the same for the next ring inside. It's slightly shorter, so its unrolled strip will be too.") as tracker:
            # Define the second ring from the circle
            r_1_mid = r - 1.5 * dr
            ring_1 = Annulus(
                inner_radius=r_1_mid - dr / 2,
                outer_radius=r_1_mid + dr / 2,
                color=BLUE,
                fill_opacity=0.7
            ).move_to(circle_center)

            # Define its corresponding rectangular strip
            strip_1 = Rectangle(
                width=2 * PI * r_1_mid,
                height=dr,
                color=BLUE,
                fill_opacity=0.7,
                stroke_width=1.5
            ).next_to(base_strip, UP, buff=0, aligned_edge=LEFT)

            # Animate the ring appearing and transforming into the strip
            self.play(FadeIn(ring_1), run_time=1.0)
            self.play(
                ReplacementTransform(ring_1, strip_1, path_arc=-PI/2),
                run_time=max(0.1, tracker.duration - 1.0)
            )
            stacked_strips.add(strip_1)
            last_strip_animated = strip_1

        with self.voiceover(text="If we keep doing this for every single ring, from the outside all the way to the center...") as tracker:
            rings_to_unroll = 10
            
            rings = VGroup()
            strips = VGroup()
            
            last_strip_ref = last_strip_animated
            
            # Create all mobjects before animating
            for i in range(2, 2 + rings_to_unroll):
                r_mid = r - (i + 0.5) * dr
                
                ring = Annulus(
                    inner_radius=r_mid - dr / 2,
                    outer_radius=r_mid + dr / 2,
                    color=BLUE,
                    fill_opacity=0.7
                ).move_to(circle_center)
                rings.add(ring)
                
                strip = Rectangle(
                    width=2 * PI * r_mid,
                    height=dr,
                    color=BLUE,
                    fill_opacity=0.7,
                    stroke_width=1.5
                ).next_to(last_strip_ref, UP, buff=0, aligned_edge=LEFT)
                strips.add(strip)
                
                last_strip_ref = strip

            # Create the list of transformation animations, using path_arc to avoid the "blob" effect
            animations = [
                ReplacementTransform(rings[j], strips[j], path_arc=-PI/2)
                for j in range(rings_to_unroll)
            ]
            
            # Play animations with a lag to show a continuous process
            self.play(
                LaggedStart(*animations, lag_ratio=0.45, run_time=tracker.duration)
            )
            stacked_strips.add(*strips)

        self.wait(4)