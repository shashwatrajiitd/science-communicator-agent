from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
import numpy as np

class FormingTheRectangle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en", tld="com"))

        n = 5
        dot_radius = 0.12
        spacing = 0.3  # Increased spacing slightly for clarity

        def create_dot_triangle(num_rows, color):
            triangle = VGroup()
            for i in range(1, num_rows + 1):
                row = VGroup(*[Dot(radius=dot_radius, color=color) for _ in range(i)])
                row.arrange(RIGHT, buff=spacing)
                triangle.add(row)
            triangle.arrange(DOWN, buff=spacing, aligned_edge=LEFT)
            return triangle

        # The scene starts with the blue triangle already present.
        blue_triangle = create_dot_triangle(n, BLUE)
        blue_triangle.move_to(LEFT * 3.5)
        self.add(blue_triangle)

        with self.voiceover(text="Now for the clever part. Let's make an exact copy of our triangle.") as tracker:
            red_triangle = blue_triangle.copy().set_color(RED)
            self.play(
                Create(red_triangle.next_to(blue_triangle, RIGHT, buff=1.5)),
                run_time=tracker.duration
            )

        with self.voiceover(text="Next, we rotate this second triangle one hundred and eighty degrees...") as tracker:
            self.play(
                Rotate(red_triangle, angle=PI, about_point=red_triangle.get_center()),
                run_time=tracker.duration
            )

        with self.voiceover(text="...and slot it right next to the first one. Together, they form a perfect rectangle.") as tracker:
            # Pre-calculate the final positions for a smooth animation
            # where both triangles move to form a centered rectangle.
            final_blue = blue_triangle.copy()
            final_red = red_triangle.copy()
            
            # Manually position the red triangle to fit perfectly
            final_red.align_to(final_blue, UP)
            final_red.next_to(final_blue, RIGHT, buff=spacing)

            rectangle_group_final = VGroup(final_blue, final_red).center()
            
            self.play(
                blue_triangle.animate.move_to(final_blue.get_center()),
                red_triangle.animate.move_to(final_red.get_center()),
                run_time=tracker.duration
            )

        rectangle = VGroup(blue_triangle, red_triangle)

        with self.voiceover(text="The height of this rectangle is our original number, 'n', which is 5. And its width is exactly one more than that, 'n plus 1'.") as tracker:
            brace_v = Brace(rectangle, direction=LEFT, buff=0.25)
            label_v = MathTex(r"n", font_size=36).next_to(brace_v, LEFT, buff=0.2)
            
            brace_h = Brace(rectangle, direction=DOWN, buff=0.25)
            label_h = MathTex(r"n+1", font_size=36).next_to(brace_h, DOWN, buff=0.2)
            
            self.play(
                GrowFromCenter(brace_v),
                Write(label_v),
                GrowFromCenter(brace_h),
                Write(label_h),
                run_time=tracker.duration
            )
        
        braces_and_labels = VGroup(brace_v, label_v, brace_h, label_h)

        with self.voiceover(text="The total number of dots here is n times n plus 1. Since this is made of two of our triangles, the original sum must be half of that.") as tracker:
            # Split the animation to match the two-part narration.
            formula1 = MathTex(r"n(n+1)", font_size=36).next_to(braces_and_labels, DOWN, buff=0.5)
            split_duration = tracker.duration * 0.45
            
            self.play(Write(formula1), run_time=split_duration)
            
            formula2 = MathTex(r"\frac{n(n+1)}{2}", font_size=36).move_to(formula1.get_center())
            self.play(
                blue_triangle.animate.shift(LEFT * 1.5),
                red_triangle.animate.shift(RIGHT * 1.5),
                FadeOut(braces_and_labels),
                TransformMatchingTex(formula1, formula2),
                run_time=tracker.duration - split_duration
            )

        with self.voiceover(text="And this simple, beautiful formula works for any number 'n'.") as tracker:
            final_formula = MathTex(r"\text{Sum} = \frac{n(n+1)}{2}", font_size=42).center()
            
            # Create a dummy mobject from formula2 to transform from
            current_formula_group = VGroup(formula2)

            self.play(
                FadeOut(blue_triangle, red_triangle),
                TransformMatchingTex(current_formula_group, final_formula),
                run_time=tracker.duration
            )

        self.wait(1)