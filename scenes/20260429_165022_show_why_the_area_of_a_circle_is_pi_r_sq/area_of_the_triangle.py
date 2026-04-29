from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class AreaOfTheTriangle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Define layout zones
        triangle_pos = LEFT * 3.5
        formula_pos = RIGHT * 3

        # Create a triangle to represent the unrolled circle
        triangle = Polygon(
            [-2.5, -1.5, 0], [2.5, -1.5, 0], [0, 1.5, 0],
            color=BLUE, fill_opacity=0.6
        )
        triangle.move_to(triangle_pos)

        # Define the area formula, broken into parts for transformation
        formula_area = MathTex(
            r"\text{Area}", r" = ", r"\frac{1}{2}", r" \cdot ", r"\text{base}", r" \cdot ", r"\text{height}",
            font_size=36
        )
        formula_area.move_to(formula_pos)

        with self.voiceover(text="The area of this new triangle must be the same as the area of our original circle. And we know how to find the area of a triangle: it's one-half of its base times its height.") as tracker:
            self.play(
                Create(triangle),
                Write(formula_area),
                run_time=tracker.duration
            )

        # Draw and label the height of the triangle
        height_line = DashedLine(triangle.get_top(), triangle.get_bottom(), color=YELLOW)
        height_label = MathTex(r"r", font_size=36, color=YELLOW).next_to(height_line, RIGHT, buff=0.2)

        with self.voiceover(text="What is the height? It's the distance from the first ring to the last, which is just the radius of the original circle.") as tracker:
            self.play(
                Create(height_line),
                Write(height_label),
                run_time=tracker.duration
            )

        # Highlight and label the base of the triangle
        base_line = Line(triangle.get_corner(DL), triangle.get_corner(DR), color=ORANGE, stroke_width=6)
        base_label = MathTex(r"2\pi r", font_size=36, color=ORANGE).next_to(base_line, DOWN, buff=0.2)

        with self.voiceover(text="And the base? That's the longest line, from the outermost ring, which has a length equal to the circle's full circumference: two pi r.") as tracker:
            self.play(
                Create(base_line),
                Write(base_label),
                run_time=tracker.duration
            )

        # Define the formulas for substitution and simplification
        formula_sub = MathTex(
            r"\text{Area}", r" = ", r"\frac{1}{2}", r" \cdot (", r"2", r"\pi r) \cdot ", r"r",
            font_size=36
        ).move_to(formula_pos)
        
        formula_final = MathTex(
            r"\text{Area} = ", r"\pi r^2",
            font_size=42
        ).move_to(formula_pos)

        with self.voiceover(text="Plugging those in, we get one-half times 2 pi r, times r. The one-half and the two cancel out, leaving us with... pi r squared.") as tracker:
            # Create copies of labels to animate their substitution into the formula
            base_label_copy = base_label.copy()
            height_label_copy = height_label.copy()

            # Define the sequence of animations
            anim_move_labels = AnimationGroup(
                base_label_copy.animate.move_to(formula_area[4]),
                height_label_copy.animate.move_to(formula_area[6])
            )
            
            anim_substitute = AnimationGroup(
                FadeOut(formula_area, base_label_copy, height_label_copy),
                FadeIn(formula_sub)
            )

            anim_cancel = AnimationGroup(
                Indicate(formula_sub[2], color=RED), # 1/2
                Indicate(formula_sub[4], color=RED)  # 2
            )

            anim_transform = ReplacementTransform(formula_sub, formula_final)
            
            anim_glow = Indicate(formula_final[1], color=YELLOW, scale_factor=1.2)

            # Play the animations in succession to match the narration
            self.play(
                Succession(
                    anim_move_labels,
                    anim_substitute,
                    anim_cancel,
                    anim_transform,
                    anim_glow
                ),
                run_time=tracker.duration
            )

        self.wait(1)