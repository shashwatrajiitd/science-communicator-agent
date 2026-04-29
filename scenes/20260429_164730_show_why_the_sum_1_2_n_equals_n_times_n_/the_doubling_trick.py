from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheDoublingTrick(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Scene setup
        n = 5
        dot_radius = 0.12
        dot_spacing = 0.4
        
        # Create the first triangle of dots
        rows = VGroup()
        for i in range(1, n + 1):
            row = VGroup(*[Dot(radius=dot_radius) for _ in range(i)])
            row.arrange(RIGHT, buff=dot_spacing)
            rows.add(row)
        
        triangle1 = rows.arrange(DOWN, buff=dot_spacing, aligned_edge=LEFT)
        triangle1.set_color(YELLOW)
        triangle1.move_to(LEFT * 3)
        self.add(triangle1)

        # Beat 1: Duplicate the triangle
        with self.voiceover(text="Now for a clever trick. Let's make an exact copy of our triangle, but in a different color.") as tracker:
            triangle2 = triangle1.copy().set_color(BLUE)
            triangle2.next_to(triangle1, RIGHT, buff=1.5)
            self.play(FadeIn(triangle2, shift=UP), run_time=tracker.duration)

        # Beat 2: Rotate and combine
        with self.voiceover(text="If we rotate this copy and slide it into place, they fit together perfectly to form a rectangle.") as tracker:
            # Animate the rotation and relative move
            self.play(
                Rotate(triangle2, angle=PI),
                triangle2.animate.next_to(triangle1, RIGHT, buff=-2*dot_radius, aligned_edge=UP),
                run_time=tracker.duration * 0.7
            )
            # Center the result
            rectangle_group = VGroup(triangle1, triangle2)
            self.play(rectangle_group.animate.move_to(ORIGIN), run_time=tracker.duration * 0.3)

        # Beat 3: Label the width
        with self.voiceover(text="What are the dimensions of this rectangle? Its width is just our number 'n', which is 5 in this case.") as tracker:
            # The bottom row is the last VGroup in triangle1
            bottom_row = triangle1.submobjects[-1]
            brace_width = Brace(bottom_row, DOWN, buff=0.2)
            label_width = MathTex(r"n", font_size=36).next_to(brace_width, DOWN, buff=0.2)
            self.play(
                Create(brace_width),
                Write(label_width),
                run_time=tracker.duration
            )

        # Beat 4: Label the height
        with self.voiceover(text="And its height is exactly one more than its width, so the height is 'n plus one'.") as tracker:
            rectangle_group = VGroup(triangle1, triangle2)
            brace_height = Brace(rectangle_group, LEFT, buff=0.2)
            label_height = MathTex(r"n+1", font_size=36).next_to(brace_height, LEFT, buff=0.2)
            self.play(
                Create(brace_height),
                Write(label_height),
                run_time=tracker.duration
            )
        
        # Beat 5: Show the rectangle's area formula
        with self.voiceover(text="The total number of dots in this rectangle is simply n times n plus one.") as tracker:
            formula1 = MathTex(r"\text{Total dots} = n \cdot (n+1)", font_size=36)
            formula1.to_edge(UP, buff=0.5)
            self.play(Write(formula1), run_time=tracker.duration)

        # Beat 6: Derive the final formula
        with self.voiceover(text="But remember, this rectangle is made of two of our original triangles. So the number of dots in just one triangle is half of that, which gives us the famous formula.") as tracker:
            formula2 = MathTex(r"\text{Sum} = \frac{n(n+1)}{2}", font_size=42)
            formula2.to_edge(UP, buff=0.5)

            # Split animation into two parts for better timing
            anim_duration = tracker.duration / 2
            
            self.play(
                triangle1.animate.shift(LEFT),
                triangle2.animate.shift(RIGHT),
                FadeOut(brace_width, label_width, brace_height, label_height),
                TransformMatchingTex(formula1, formula2),
                run_time=anim_duration
            )
            self.play(
                Circumscribe(formula2, color=YELLOW, time_width=2),
                run_time=anim_duration
            )
        
        self.wait(1)