from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
import numpy as np

class FormingTheRectangle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en", tld="com"))

        # Setup: Create the initial triangle of dots
        n = 5
        dot_config = {"radius": 0.12, "color": BLUE}
        
        rows = []
        for i in range(1, n + 1):
            row = VGroup(*[Dot(**dot_config) for _ in range(i)])
            row.arrange(RIGHT, buff=0.25)
            rows.append(row)
        
        dots_blue = VGroup(*rows).arrange(DOWN, buff=0.25, aligned_edge=LEFT)
        dots_blue.center().shift(LEFT * 2.5 + UP * 0.5)

        self.add(dots_blue)
        
        with self.voiceover(text="The trick is to take a second, identical copy of our triangle.") as tracker:
            dots_red = dots_blue.copy().set_color(RED)
            dots_red.next_to(dots_blue, RIGHT, buff=1.5)
            self.play(
                GrowFromCenter(dots_red),
                run_time=tracker.duration
            )

        with self.voiceover(text="Now, let's rotate this copy and see how it fits with the first one.") as tracker:
            # Calculate final positions for a centered rectangle
            final_group = VGroup(
                dots_blue.copy(),
                dots_red.copy().rotate(PI)
            ).arrange(RIGHT, buff=0.25, aligned_edge=UP).center().shift(UP * 0.5)
            
            blue_target_pos = final_group[0].get_center()
            red_target_pos = final_group[1].get_center()

            self.play(
                dots_blue.animate.move_to(blue_target_pos),
                Rotate(dots_red, angle=PI, about_point=dots_red.get_center()),
                dots_red.animate.move_to(red_target_pos),
                run_time=tracker.duration
            )

        with self.voiceover(text="Together, they form a perfect rectangle. Its height is still 'n', but its width is now 'n' plus one extra column.") as tracker:
            rectangle_group = VGroup(dots_blue, dots_red)
            rect_highlight = SurroundingRectangle(rectangle_group, color=YELLOW, buff=0.2)
            
            height_label = MathTex(r"n", font_size=36).next_to(rectangle_group, LEFT, buff=0.5)
            width_label = MathTex(r"n+1", font_size=36).next_to(rectangle_group, DOWN, buff=0.5)
            
            labels = VGroup(height_label, width_label)

            self.play(
                Create(rect_highlight),
                Write(labels),
                run_time=tracker.duration
            )

        with self.voiceover(text="The total number of dots in this rectangle is n times (n+1). Since our original triangle is exactly half of this, its sum must be n times (n+1), divided by two.") as tracker:
            # The caption zone
            formula_total = MathTex(r"\text{Total dots} = n(n+1)", font_size=36)
            formula_total.to_edge(DOWN, buff=0.5)

            formula_sum = MathTex(r"\text{Sum} = \frac{n(n+1)}{2}", font_size=36)
            formula_sum.to_edge(DOWN, buff=0.5)

            # Animate the first part of the sentence
            self.play(
                FadeOut(rect_highlight),
                Write(formula_total),
                run_time=tracker.duration * 0.5
            )

            # Animate the second part
            self.play(
                FadeOut(dots_red, shift=RIGHT),
                FadeOut(labels),
                TransformMatchingTex(formula_total, formula_sum),
                run_time=tracker.duration * 0.5
            )

        self.wait(1)