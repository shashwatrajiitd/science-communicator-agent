from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class UnrollRingsToTriangleAUnrollOuterRing(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # --- Scene Setup ---
        r = 2.0
        dr = 0.1 # Thickness of the ring
        circumference = 2 * PI * r

        # Camera setup omitted — default frame is used.

        # --- Initial Objects ---
        # A circle from which the ring originates. Positioned at the top center of the view.
        # This matches the 'the_circle' shared object spec.
        circle_pos = RIGHT * (circumference / 2) + UP * 4
        the_circle = Circle(radius=r, color=BLUE).move_to(circle_pos)

        # The outermost ring, which we will unroll.
        outer_ring = Annulus(
            inner_radius=r - dr,
            outer_radius=r,
            color=YELLOW,
            fill_opacity=1.0,
            stroke_width=0
        ).move_to(the_circle.get_center())

        # Group for easy management
        initial_group = VGroup(the_circle, outer_ring)
        self.add(initial_group)
        self.wait(0.5) # Brief pause to show the initial state

        # --- Beat 1: Unroll the ring ---
        with self.voiceover(text="When we unroll it, it becomes a long, thin strip. The length of this strip is just the circumference of that outer ring...") as tracker:
            # The target shape: a thin rectangle representing the unrolled ring.
            # Its dimensions match the circumference and ring thickness.
            unrolled_rect = Rectangle(
                width=circumference,
                height=dr,
                color=YELLOW,
                fill_opacity=1.0,
                stroke_width=0
            )
            # Position its bottom-left corner at the origin. This is crucial for
            # correctly forming the right-angled triangle in subsequent scenes.
            unrolled_rect.move_to(ORIGIN, aligned_edge=DL)

            # Animate the ring moving down and transforming into the flat rectangle.
            self.play(
                Transform(outer_ring, unrolled_rect),
                FadeOut(the_circle),
                run_time=tracker.duration
            )

        # --- Beat 2: Label the length ---
        with self.voiceover(text="...which we know is 2 times pi times the radius, r.") as tracker:
            # After the Transform, the `outer_ring` mobject is now the rectangle.
            # We label its length, which corresponds to the 'circumference_line' shared object.
            brace = Brace(outer_ring, direction=DOWN, buff=0.25)
            label = MathTex(r"2\pi r", font_size=36).next_to(brace, DOWN, buff=0.25)

            self.play(
                GrowFromCenter(brace),
                Write(label),
                run_time=tracker.duration
            )

        # A brief pause at the end of the scene.
        self.wait(1)