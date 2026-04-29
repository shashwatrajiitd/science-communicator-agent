from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class UnrollRingsToTriangleCFormTheTriangle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # --- CONFIGURATION ---
        R = 2.0
        C_LEN = 2 * PI * R
        N_RINGS = 50
        dr = R / N_RINGS

        # --- POSITIONING ---
        # Center the final triangle shape on the screen.
        # The triangle's bounding box is (C_LEN x R).
        # We define the triangle's bottom-left origin such that its bounding box is centered at ORIGIN.
        triangle_origin = -np.array([C_LEN / 2, R / 2, 0])

        # --- MOBJECT CREATION ---
        # Create the initial rings, all starting at the center for the animation.
        rings = VGroup()
        # Iterate from outermost to innermost
        for i in range(N_RINGS):
            r_outer = R - i * dr
            r_inner = R - (i + 1) * dr
            ring = Annulus(
                inner_radius=r_inner,
                outer_radius=r_outer,
                color=BLUE,
                fill_opacity=1,
                stroke_width=0.5
            ).move_to(ORIGIN)
            rings.add(ring)

        # Create the final unrolled rectangles, positioned to form a right-angled triangle.
        rects = VGroup()
        for i in range(N_RINGS):
            r_outer = R - i * dr
            r_inner = R - (i + 1) * dr
            avg_radius = (r_outer + r_inner) / 2
            unrolled_len = 2 * PI * avg_radius
            
            rect = Rectangle(
                height=dr,
                width=unrolled_len,
                color=BLUE,
                fill_opacity=1,
                stroke_width=0.5,
                stroke_color=WHITE
            )
            
            # This is the key fix: align all rectangles by their bottom-left corner
            # to form a vertical left edge. The i-th ring from the outside becomes
            # the i-th rectangle from the bottom.
            rect.move_to(triangle_origin + np.array([0, i * dr, 0]), aligned_edge=DL)
            rects.add(rect)

        # --- SHARED OBJECTS (positioned for this scene) ---
        
        # unrolled_triangle spec: right-angled, vertices (0,0), (12.566, 0), (0, 2.0)
        # We create it with vertices relative to the calculated triangle_origin.
        verts_abs = [
            triangle_origin,
            triangle_origin + np.array([C_LEN, 0, 0]),
            triangle_origin + np.array([0, R, 0])
        ]
        unrolled_triangle_outline = Polygon(*verts_abs, color=GREEN, stroke_width=6)
        
        # circumference_line spec: line from (0,0) to (12.566,0), color YELLOW, label "2πr"
        circumference_line = Line(verts_abs[0], verts_abs[1], color=YELLOW, stroke_width=6)
        circumference_label = MathTex(r"2\pi r", font_size=36, color=YELLOW).next_to(circumference_line, DOWN, buff=0.2)
        
        # The scene starts with the rings ready to be unrolled.
        self.add(rings)
        
        # --- ANIMATION ---
        narration_text = "...what we end up with is a shape that looks remarkably like a triangle."
        with self.voiceover(text=narration_text) as tracker:
            # The animation is deliberately longer than the short narration to give the viewer
            # time to process the transformation.
            unroll_duration = 5.0
            outline_duration = 2.0

            self.play(
                LaggedStart(
                    *[Transform(rings[i], rects[i]) for i in range(N_RINGS)],
                    lag_ratio=0.1,
                    run_time=unroll_duration
                )
            )
            
            self.play(
                Create(unrolled_triangle_outline),
                Create(circumference_line),
                Write(circumference_label),
                run_time=outline_duration
            )

        # Pause to let the viewer absorb the final result and meet the target duration.
        self.wait(8)