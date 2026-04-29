from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class UnrollRingsToTriangleCFormTheTriangle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Parameters from shared objects
        r = 2.0
        circ = 2 * np.pi * r
        n_rings = 100
        dr = r / n_rings

        # Layout zones
        center_zone = ORIGIN
        caption_zone = DOWN * 2

        # Shared Object: the_circle
        the_circle = Circle(radius=r, color=BLUE).move_to(center_zone + UP * 1.5)

        # Create source rings inside the circle
        rings = VGroup()
        # Fix for issue #4: Rings are shades of BLUE
        ring_colors = [interpolate_color(BLUE_E, BLUE_B, i / n_rings) for i in range(n_rings)]
        for i in range(n_rings):
            # Rings from outside in
            outer_r = r * (n_rings - i) / n_rings
            inner_r = r * (n_rings - i - 1) / n_rings
            if inner_r < 0: inner_r = 0
            ring = Annulus(
                inner_radius=inner_r,
                outer_radius=outer_r,
                fill_opacity=1,
                stroke_width=0,
                color=ring_colors[i]
            ).move_to(the_circle.get_center())
            rings.add(ring)

        # Create target rectangles that will form the triangle
        rects = VGroup()
        # Fix for issue #3: Rectangles are shades of GREEN
        rect_colors = [interpolate_color(GREEN_E, GREEN_B, i / n_rings) for i in range(n_rings)]
        for i in range(n_rings):
            # Outermost ring (i=0) becomes the longest rectangle (the base)
            rect_r = r * (n_rings - i - 0.5) / n_rings
            rect_circ = 2 * np.pi * rect_r
            rect = Rectangle(
                width=rect_circ,
                height=dr,
                fill_opacity=1,
                stroke_width=0,
                color=rect_colors[i]
            )
            rects.add(rect)

        # Fix for issue #1: Arrange rectangles to form a perfect right-angled triangle
        rects.arrange(DOWN, buff=0)
        rects.align_to(rects[0], LEFT) # Align all left edges to the first (bottom) rect
        rects.move_to(caption_zone)

        # Shared Object: unrolled_triangle (outline)
        v0 = rects.get_corner(DL) # Bottom-left
        v1 = rects.get_corner(DR) # Bottom-right
        v2 = rects.get_corner(UL) # Top-left
        
        # Shared Object: circumference_line
        circumference_line = Line(v0, v1, color=YELLOW, stroke_width=6)
        height_line = Line(v0, v2, color=GREEN, stroke_width=6)
        hypotenuse = Line(v1, v2, color=GREEN, stroke_width=6)
        unrolled_triangle = VGroup(circumference_line, height_line, hypotenuse)

        circumference_label = MathTex(r"2\pi r", font_size=36, color=YELLOW)
        circumference_label.next_to(circumference_line, DOWN, buff=0.2)

        # Start scene with the circle and its component rings
        self.add(the_circle, rings)
        
        with self.voiceover(text="...what we end up with is a shape that looks remarkably like a triangle.") as tracker:
            # Split the animation into two parts within the voiceover duration
            transform_time = tracker.duration * 0.7
            outline_time = tracker.duration * 0.3

            # The main animation: transform rings into the stacked rectangles
            self.play(
                LaggedStart(
                    *[
                        Transform(rings[i], rects[i]) for i in range(n_rings)
                    ],
                    lag_ratio=0.05,
                ),
                FadeOut(the_circle),
                run_time=transform_time
            )

            # Emphasize the final shape by drawing the triangle outline and label
            self.play(
                Create(unrolled_triangle),
                Write(circumference_label),
                run_time=outline_time
            )