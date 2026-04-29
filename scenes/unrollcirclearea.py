from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
import numpy as np

class UnrollCircleArea(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en", tld="com"))

        # ZONES
        title_zone = UP * 3.5
        caption_zone = DOWN * 3.5
        center_zone = ORIGIN

        # =================================================================
        # SECTION 1: HOOK - The Formula
        # =================================================================
        title = Tex("The Area of a Circle", font_size=42).move_to(title_zone)
        formula = MathTex(r"A = \pi r^2", font_size=48).move_to(center_zone)

        with self.voiceover(text="We all learn in school that the area of a circle is Pi R squared. But why? Let's build an intuition for where this famous formula actually comes from.") as tracker:
            self.play(Write(title), run_time=tracker.duration/2)
            self.play(Write(formula), run_time=tracker.duration/2)
        self.wait(0.5)

        # =================================================================
        # SECTION 2: CONCENTRIC RINGS
        # =================================================================
        
        radius = 2.0
        circle = Circle(radius=radius, color=BLUE, stroke_width=8).move_to(center_zone)
        
        num_rings = 10
        rings = VGroup(*[
            Annulus(
                inner_radius=r * (radius / num_rings),
                outer_radius=(r + 0.75) * (radius / num_rings),
                color=BLUE,
                fill_opacity=1.0
            ) for r in range(num_rings)
        ]).move_to(center_zone)
        
        caption1 = Text(
            "Imagine a circle is made of many thin, concentric rings.",
            font_size=28
        ).move_to(caption_zone)

        with self.voiceover(text="First, imagine a circle isn't a single flat shape, but is instead built from a huge number of incredibly thin, nested rings, almost like the rings of a tree.") as tracker:
            self.play(
                FadeOut(title, formula),
                Create(circle),
                run_time=1.5
            )
            self.play(
                LaggedStart(
                    *[Create(ring) for ring in rings],
                    lag_ratio=0.1
                ),
                Write(caption1),
                run_time=tracker.duration - 1.5
            )

        self.wait(0.5)
        
        # =================================================================
        # SECTION 3: UNROLLING THE RINGS
        # =================================================================

        # Group elements for easy cleanup
        center_group = VGroup(circle, rings)

        # Create the triangle from rectangles
        rects = VGroup()
        for i, ring in enumerate(rings):
            r = (i + 0.5) * (radius / num_rings)
            height = radius / num_rings
            width = 2 * PI * r
            rect = Rectangle(
                width=width,
                height=height,
                fill_color=BLUE,
                fill_opacity=1,
                stroke_width=1,
                stroke_color=BLACK,
            )
            rect.move_to(
                (width/2 - PI*radius) * RIGHT + (i * height - radius/2) * UP,
                aligned_edge=DL
            )
            rects.add(rect)
        
        triangle = Polygon(
            [-PI * radius, -radius, 0],
            [PI * radius, -radius, 0],
            [0, radius, 0],
            fill_opacity=0 # This is just for alignment/braces
        ).move_to(center_zone)
        rects.move_to(triangle.get_center_of_mass())

        caption2 = Text(
            "If we cut each ring and lay it flat, they form a new shape.",
            font_size=28
        ).move_to(caption_zone)
        
        with self.voiceover(text="Now, if we could take every single ring, from the tiny one at the center to the largest one at the edge, cut them, and stack them up, they would form a new shape.") as tracker:
            self.play(
                Transform(caption1, caption2),
                ReplacementTransform(center_group, rects),
                run_time=tracker.duration
            )

        self.wait(0.5)

        # =================================================================
        # SECTION 4: THE TRIANGLE AND ITS DIMENSIONS
        # =================================================================
        
        final_triangle = Polygon(
            triangle.get_vertices()[0],
            triangle.get_vertices()[1],
            triangle.get_vertices()[2],
            stroke_color=BLUE,
            fill_color=BLUE,
            fill_opacity=1
        ).move_to(rects.get_center())

        with self.voiceover(text="As the rings get infinitely thin, this shape becomes a perfect triangle.") as tracker:
            self.play(
                FadeOut(caption1),
                FadeIn(final_triangle),
                FadeOut(rects),
                run_time=tracker.duration
            )
        
        # Add braces and labels
        brace_h = Brace(final_triangle, direction=LEFT, buff=0.2)
        label_h = MathTex(r"r", font_size=36).next_to(brace_h, LEFT)

        brace_b = Brace(final_triangle, direction=DOWN, buff=0.2)
        label_b = MathTex(r"2 \pi r", font_size=36).next_to(brace_b, DOWN)

        caption3_line1 = Text("The triangle's height is the circle's radius, 'r'.", font_size=28)
        caption3_line2 = Text("The base is the outer circumference, '2 * pi * r'.", font_size=28)
        caption3 = VGroup(caption3_line1, caption3_line2).arrange(DOWN, buff=0.15).move_to(caption_zone)

        with self.voiceover(text="What are the dimensions of this triangle? Its height is simply the radius of the original circle. And its base is the unrolled outer ring, which has a length equal to the circle's full circumference, 2 pi r.") as tracker:
            self.play(
                Create(brace_h),
                Write(label_h),
                run_time=tracker.duration/2
            )
            self.play(
                Create(brace_b),
                Write(label_b),
                Write(caption3),
                run_time=tracker.duration/2
            )
        
        self.wait(0.5)

        # Cleanup for final calculation
        center_objects = VGroup(final_triangle, brace_h, label_h, brace_b, label_b)

        # =================================================================
        # SECTION 5: THE PAYOFF
        # =================================================================
        
        formula_area_tri = MathTex(r"A_{triangle} = \frac{1}{2} \cdot \text{base} \cdot \text{height}", font_size=36)
        formula_area_sub = MathTex(r"A = \frac{1}{2} \cdot (2 \pi r) \cdot (r)", font_size=36)
        formula_area_final = MathTex(r"A = \pi r^2", font_size=42, color=YELLOW)

        formulas = VGroup(formula_area_tri, formula_area_sub, formula_area_final).arrange(DOWN, buff=0.7).move_to(center_zone)
        formula_area_sub.align_to(formula_area_tri, LEFT)
        formula_area_final.align_to(formula_area_tri, LEFT)

        with self.voiceover(text="We know the area of a triangle is one-half times base times height. Plugging in our new dimensions gives us one-half of two pi r, times r.") as tracker:
            self.play(
                FadeOut(center_objects, caption3),
                run_time=1
            )
            self.play(Write(formula_area_tri), run_time=tracker.duration - 2)
            self.play(TransformMatchingTex(formula_area_tri.copy(), formula_area_sub), run_time=1)

        self.wait(0.5)

        with self.voiceover(text="The one-half and the two cancel out perfectly, leaving us with... pi r squared. And that's it!") as tracker:
            self.play(
                TransformMatchingTex(formula_area_sub.copy(), formula_area_final),
                run_time=tracker.duration
            )

        self.wait(0.5)

        with self.voiceover(text="By rearranging the rings that make up the circle, we can see why its area is exactly pi times its radius squared.") as tracker:
            self.play(Circumscribe(formula_area_final, color=YELLOW, time_width=2), run_time=tracker.duration)

        self.wait(2)