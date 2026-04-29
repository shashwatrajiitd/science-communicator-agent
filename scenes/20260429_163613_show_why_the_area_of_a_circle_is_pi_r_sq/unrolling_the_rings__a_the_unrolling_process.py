from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class UnrollingTheRingsATheUnrollingProcess(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # TITLE ZONE
        title = Text("The Elegant Formula for a Circle's Area", font_size=42).to_edge(UP, buff=0.5)
        self.add(title)

        # CENTER ZONE SETUP
        R = 2.0
        N_RINGS = 10
        dr = R / N_RINGS

        # Generate rings from outermost to innermost to simplify indexing later
        rings = VGroup(*[
            Annulus(
                inner_radius=r,
                outer_radius=r + dr,
                fill_opacity=1,
                stroke_width=0,
                color=interpolate_color(BLUE, TEAL, r / R)
            ) for r in np.arange(R - dr, -dr, -dr)
        ])
        rings.move_to(ORIGIN)
        self.add(rings)

        unrolled_lines = VGroup()
        # This stroke width visually represents the thickness of the rings (dr)
        line_stroke_width = 25

        # Beat 1: Unroll the first ring
        with self.voiceover(text="Now, let's take each of these rings, make a single cut, and unroll it into a straight line.") as tracker:
            outer_ring = rings[0]
            # Use average radius for circumference calculation
            outer_radius = (outer_ring.inner_radius + outer_ring.outer_radius) / 2
            line_length = 2 * PI * outer_radius

            line1 = Line(
                LEFT * line_length / 2,
                RIGHT * line_length / 2,
                stroke_width=line_stroke_width,
                color=outer_ring.get_color()
            ).to_edge(DOWN, buff=1.5)

            # A simple snip animation
            cut = Line(UP, DOWN, color=WHITE, stroke_width=3).scale(dr).move_to(outer_ring.get_top())
            self.play(Create(cut), run_time=0.5)
            self.play(FadeOut(cut), run_time=0.5)
            
            self.play(
                Transform(outer_ring, line1),
                run_time=tracker.duration - 1.0
            )
            unrolled_lines.add(line1)

        # Beat 2: Label the unrolled line
        with self.voiceover(text="The length of this line is the ring's circumference. For the outermost ring, that's 2 pi r.") as tracker:
            line_to_label = unrolled_lines[0]
            brace = Brace(line_to_label, DOWN, buff=0.2)
            label = MathTex(r"2\pi r", font_size=36).next_to(brace, DOWN, buff=0.2)
            
            self.play(
                FadeIn(brace, shift=UP),
                Write(label),
                run_time=tracker.duration
            )

        # Beat 3: Unroll and stack the next two rings
        with self.voiceover(text="We can do this for every single ring, stacking them up one by one.") as tracker:
            animations = []
            
            # Unroll the next two rings (at indices 1 and 2)
            for i in range(1, 3):
                ring_to_unroll = rings[i]
                radius = (ring_to_unroll.inner_radius + ring_to_unroll.outer_radius) / 2
                line_length = 2 * PI * radius
                
                prev_line = unrolled_lines[-1]
                
                new_line = Line(
                    LEFT * line_length / 2,
                    RIGHT * line_length / 2,
                    stroke_width=line_stroke_width,
                    color=ring_to_unroll.get_color()
                ).next_to(prev_line, UP, buff=0)
                
                animations.append(Transform(ring_to_unroll, new_line))
                unrolled_lines.add(new_line)

            self.play(
                FadeOut(brace, label),
                AnimationGroup(*animations, lag_ratio=0.5),
                run_time=tracker.duration
            )