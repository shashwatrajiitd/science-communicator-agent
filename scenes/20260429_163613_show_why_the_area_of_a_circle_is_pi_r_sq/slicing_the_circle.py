from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
import numpy as np

class SlicingTheCircle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en", tld="com"))

        # ZONES
        title = Text("The Elegant Formula for a Circle's Area", font_size=42).to_edge(UP, buff=0.5)
        self.add(title)

        # Main visualization setup
        R = 2.0
        N_RINGS = 20
        dr = R / N_RINGS

        rings = VGroup()
        # This loop adds rings to the VGroup from outermost to innermost
        for i in range(N_RINGS - 1, -1, -1):
            inner_radius = i * dr
            outer_radius = (i + 1) * dr
            ring = Annulus(
                inner_radius=inner_radius,
                outer_radius=outer_radius,
                fill_opacity=1,
                stroke_width=1,
                color=BLUE,
            )
            rings.add(ring)
        
        rings.move_to(ORIGIN)
        circle_outline = Circle(radius=R, color=WHITE).move_to(ORIGIN)

        with self.voiceover(text="Imagine the circle isn't a single flat shape, but is instead built from countless, thin rings nested inside each other.") as tracker:
            # reversed(rings) iterates from innermost to outermost, so the creation is from the center outwards.
            self.play(
                LaggedStart(*[Create(ring) for ring in reversed(rings)], lag_ratio=0.1),
                Create(circle_outline),
                run_time=tracker.duration
            )

        # The outermost ring is the first one we added to the VGroup.
        outer_ring = rings[0]
        
        with self.voiceover(text="Each ring is like a tiny thread of circumference. The outermost ring has a length equal to the full circumference of the circle, 2 pi r.") as tracker:
            circumference_label = MathTex(r"2\pi r", font_size=36).next_to(outer_ring, RIGHT, buff=0.5)
            self.play(
                outer_ring.animate.set_color(YELLOW).scale(1.1),
                Write(circumference_label),
                run_time=tracker.duration
            )

        with self.voiceover(text="As we move towards the center, the rings get shorter and shorter, approaching a length of zero at the very middle.") as tracker:
            # Revert the outer ring and remove the label in a quick transition
            self.play(
                FadeOut(circumference_label),
                outer_ring.animate.set_color(BLUE).scale(1/1.1),
                run_time=1.0
            )
            center_dot = Dot(ORIGIN, color=YELLOW)
            # Use the remaining time for the scan animation
            remaining_time = max(0.1, tracker.duration - 1.0)
            
            # The `rings` VGroup is already ordered from outermost to innermost,
            # so ShowPassingFlash will scan towards the center.
            self.play(
                ShowPassingFlash(
                    rings.copy().set_color(YELLOW), 
                    time_width=0.5
                ),
                GrowFromCenter(center_dot),
                run_time=remaining_time
            )

        self.wait(1)