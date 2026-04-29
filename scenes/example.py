"""Sample Manim scenes — verify the install with:

    manim -pql scenes/example.py SquareToCircle
"""

from manim import (
    Scene, Square, Circle, Create, Transform, Write, FadeIn, FadeOut,
    MathTex, Text, VGroup, BLUE, YELLOW, WHITE, UP, DOWN, LEFT, RIGHT,
)


class SquareToCircle(Scene):
    def construct(self):
        title = Text("Hello, Science Communicator", font_size=40).to_edge(UP)
        square = Square(color=BLUE, fill_opacity=0.5)
        circle = Circle(color=YELLOW, fill_opacity=0.5)

        self.play(Write(title))
        self.play(Create(square))
        self.wait(0.5)
        self.play(Transform(square, circle))
        self.wait(0.5)
        self.play(FadeOut(square), FadeOut(title))


class EulerIdentity(Scene):
    """Demonstrates LaTeX rendering — requires MacTeX/BasicTeX installed."""

    def construct(self):
        formula = MathTex(r"e^{i\pi} + 1 = 0", font_size=96)
        caption = Text("Euler's identity", font_size=32, color=WHITE).next_to(formula, DOWN)
        group = VGroup(formula, caption)

        self.play(Write(formula), run_time=2)
        self.play(FadeIn(caption, shift=UP))
        self.wait(2)
        self.play(FadeOut(group))
