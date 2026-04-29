from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class ConcentricRings(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        radius = 2.0
        n_rings = 20
        dr = radius / n_rings

        # This is the shared object, 'the_circle', defined by its boundary
        the_circle = Circle(radius=radius, color=BLUE).move_to(ORIGIN)

        # These are the dividing lines that will appear
        dividing_lines = VGroup(*[
            Circle(radius=r, color=WHITE, stroke_width=2)
            for r in np.linspace(dr, radius - dr, n_rings - 1)
        ])

        with self.voiceover(text="One way to think about the area is to slice the circle into many thin, concentric rings, like the rings of a tree.") as tracker:
            self.play(Create(the_circle), run_time=1.5)
            self.play(
                LaggedStart(
                    *[Create(line) for line in dividing_lines],
                    lag_ratio=0.1
                ),
                run_time=tracker.duration - 1.5
            )

        # Now, create the filled annuli that represent the area of each ring
        filled_rings = VGroup()
        # The innermost "ring" is a disk
        filled_rings.add(
            Circle(radius=dr, color=BLUE, fill_opacity=0.6, stroke_width=0)
        )
        # The rest are actual annuli
        for i in range(1, n_rings):
            filled_rings.add(
                Annulus(
                    inner_radius=i * dr,
                    outer_radius=(i + 1) * dr,
                    color=BLUE,
                    fill_opacity=0.6,
                    stroke_width=0
                )
            )

        with self.voiceover(text="The total area of the circle is just the sum of the areas of all these little rings.") as tracker:
            self.play(
                LaggedStart(
                    *[FadeIn(ring) for ring in filled_rings],
                    lag_ratio=0.1,
                ),
                run_time=tracker.duration
            )

        outermost_ring = filled_rings[-1]
        cut_point = outermost_ring.get_right()
        cut_mark = Line(
            cut_point + UP * 0.15,
            cut_point + DOWN * 0.15,
            color=YELLOW,
            stroke_width=6
        )

        with self.voiceover(text="Now, what happens if we take the outermost ring, snip it, and unroll it?") as tracker:
            self.play(
                outermost_ring.animate.set_color(YELLOW),
                Create(cut_mark),
                run_time=tracker.duration
            )