from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class UnrollingTheRingsBStackAllRings(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Constants for layout and geometry
        R = 2.0
        N_RINGS = 50
        circle_center = LEFT * 4
        
        # Scaled dimensions for the triangle to fit on screen
        triangle_height = 3.0
        triangle_base = 5.0
        triangle_pos = RIGHT * 1.5

        # Create the concentric rings that form the circle
        dr = R / N_RINGS
        radii = np.linspace(dr, R, N_RINGS)
        colors = color_gradient([BLUE, GREEN], N_RINGS)
        
        rings = VGroup(*[
            Annulus(
                inner_radius=r - dr,
                outer_radius=r,
                fill_opacity=1,
                stroke_width=0,
                color=colors[i]
            ) for i, r in enumerate(radii)
        ]).move_to(circle_center)

        # Beat 1: Introduce the idea of unrolling every ring.
        with self.voiceover(text="Now, imagine we do this for every single ring, from the tiny one at the very center to the largest one at the outer edge.") as tracker:
            self.play(
                LaggedStart(
                    *[FadeIn(ring) for ring in rings],
                    lag_ratio=0.05
                ),
                run_time=tracker.duration
            )

        # Beat 2: Unroll the rings and stack them into a triangular shape.
        with self.voiceover(text="If we stack all those resulting lines, organizing them from shortest to longest...") as tracker:
            # Create target rectangles that will form the triangle
            rects = VGroup()
            for i, r in enumerate(radii):
                rect_width = (r / R) * triangle_base
                rect_height = triangle_height / N_RINGS
                rect = Rectangle(
                    width=rect_width,
                    height=rect_height,
                    stroke_width=0,
                    fill_opacity=1.0,
                    color=rings[i].get_color()
                )
                rects.add(rect)
            
            # Arrange rectangles from shortest (top) to longest (bottom), aligned on the left
            rects.arrange(DOWN, buff=0, aligned_edge=LEFT)
            rects.move_to(triangle_pos, aligned_edge=UL)
            
            # Animate the transformation from rings to stacked rectangles
            self.play(
                LaggedStart(
                    *[ReplacementTransform(rings[i], rects[i]) for i in range(N_RINGS)],
                    lag_ratio=0.5 # Increased lag to show sequential stacking
                ),
                run_time=tracker.duration
            )

        # Beat 3: The stacked lines form a solid triangle.
        with self.voiceover(text="they form a new shape: a triangle.") as tracker:
            # Define the final solid right triangle based on the stacked rectangles' position
            v_tl = rects.get_corner(UL)
            v_bl = rects.get_corner(DL)
            v_br = rects.get_corner(DR)
            
            triangle = Polygon(v_tl, v_bl, v_br, color=TEAL, fill_opacity=1.0, stroke_width=0)
            
            # Replace the group of rectangles with the single solid triangle.
            self.play(
                ReplacementTransform(rects, triangle),
                run_time=tracker.duration
            )

        self.wait(1)