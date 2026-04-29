from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class SlicingIntoRings(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Setup scene with a circle, radius, and formula, as they are faded out in the first beat.
        radius_val = 2
        circle = Circle(radius=radius_val, color=BLUE, fill_opacity=0.5).move_to(ORIGIN)
        radius_line = Line(circle.get_center(), circle.get_right(), color=WHITE)
        radius_label = MathTex(r"r", font_size=36).next_to(radius_line, DOWN, buff=0.2)
        formula = MathTex(r"A = \pi r^2", font_size=42).to_edge(UP, buff=0.5)
        
        self.add(circle, radius_line, radius_label, formula)

        with self.voiceover(text="There's a beautiful way to see the answer, and it starts by reimagining the area.") as tracker:
            self.play(
                FadeOut(formula),
                FadeOut(radius_line),
                FadeOut(radius_label),
                run_time=tracker.duration
            )

        # Reduced number of rings to make the animation feel slightly quicker, addressing duration feedback.
        num_rings = 15
        rings = VGroup(*[
            Circle(radius=r, color=BLUE, stroke_width=3)
            for r in np.linspace(0.1, radius_val, num_rings)
        ]).move_to(ORIGIN)

        with self.voiceover(text="Instead of thinking of it as a single flat disc, picture it as being made up of countless, extremely thin concentric rings, nested inside each other like the rings of a tree.") as tracker:
            self.play(
                FadeOut(circle), # Fade out the filled disc
                AnimationGroup(*[Create(ring) for ring in rings], lag_ratio=0.1),
                run_time=tracker.duration
            )

        # Correctly highlight a single ring and dim the others.
        highlight_index = 7 # A ring in the middle of 15 rings.
        highlighted_ring = rings[highlight_index]
        other_rings = VGroup(*[rings[i] for i in range(num_rings) if i != highlight_index])

        with self.voiceover(text="Let's focus on just one of these rings.") as tracker:
            self.play(
                highlighted_ring.animate.set_color(YELLOW).set_stroke(width=5),
                other_rings.animate.set_opacity(0.4),
                run_time=tracker.duration
            )