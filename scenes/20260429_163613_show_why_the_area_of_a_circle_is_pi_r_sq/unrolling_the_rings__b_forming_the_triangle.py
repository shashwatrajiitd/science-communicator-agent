from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
import numpy as np

class UnrollingTheRingsBFormingTheTriangle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en", tld="com"))

        # Define triangle properties for the visualization
        base_width = 8.0
        height = 4.0
        n_lines = 100
        line_color = TEAL
        triangle_color = BLUE

        # Define the vertices for a right-angled triangle, starting in the first quadrant
        # for simpler geometric calculations. The right angle is at the origin.
        v_origin = ORIGIN
        v_base = RIGHT * base_width
        v_height = UP * height

        # Create a VGroup of horizontal lines that will form the triangle.
        # This approach ensures the top line has zero length, forming a perfect triangle.
        lines = VGroup()
        y_coords = np.linspace(v_origin[1], v_height[1], n_lines)

        for y in y_coords:
            # The length of the horizontal line (x_end) decreases linearly with height.
            # This is derived from the equation of the hypotenuse connecting v_base and v_height.
            x_end = (base_width / height) * (height - y)
            line = Line(
                start=[v_origin[0], y, 0],
                end=[x_end, y, 0],
                stroke_width=3,  # Make lines slightly thicker to look more solid
                color=line_color
            )
            lines.add(line)
        
        # Center the entire group of lines on the screen for better viewing.
        lines.move_to(ORIGIN)

        # Beat 1: Animate the rapid stacking of unrolled rings (lines)
        with self.voiceover(text="As we stack all the unrolled rings, from the longest at the bottom to the shortest at the top...") as tracker:
            self.play(
                LaggedStart(
                    *(Create(line) for line in lines),
                    lag_ratio=0.1,
                    run_time=tracker.duration
                )
            )

        # Beat 2: Transform the stack of lines into a solid, filled triangle
        # Create the final polygon with the same geometric definition as the lines.
        final_triangle = Polygon(
            v_origin, v_base, v_height,
            color=triangle_color,
            fill_opacity=0.7,
            stroke_width=0
        )
        # Move the final triangle to the same position as the group of lines.
        final_triangle.move_to(lines.get_center())

        with self.voiceover(text="...they form a shape that looks remarkably like a right-angled triangle.") as tracker:
            self.play(
                ReplacementTransform(lines, final_triangle),
                run_time=tracker.duration
            )
        
        self.wait(1)