import numpy as np
from manim import *

class PiInNormalDistribution(Scene):
    """
    An animation explaining the origin of pi in the normal distribution
    by solving the Gaussian integral using polar coordinates.
    """
    def construct(self):
        # 1. Introduction: The mystery of pi
        title = Text("Why is π in the Normal Distribution?").to_edge(UP)
        normal_dist = MathTex(
            r"f(x) = \frac{1}{\sqrt{2", r"\pi", r"\sigma^2}} e^{-\frac{(x-\mu)^2}{2\sigma^2}}"
        ).scale(1.1)

        self.play(Write(title))
        self.play(Write(normal_dist))
        self.wait(1)
        self.play(Indicate(normal_dist.get_part_by_tex(r"\pi"), color=YELLOW, scale_factor=1.5))
        self.wait(1.5)

        # 2. Simplify to the core problem: The Gaussian Integral
        caption1 = Text("The answer lies in the Gaussian Integral:").to_edge(UP)
        gaussian_integral = MathTex(r"I = \int_{-\infty}^{\infty} e^{-x^2} dx").scale(1.2)

        self.play(ReplacementTransform(title, caption1), FadeOut(normal_dist, shift=DOWN))
        self.play(Write(gaussian_integral))
        self.wait(2)

        # 3. The trick: Square the integral in two dimensions
        caption2 = Text("The trick is to square it in two dimensions.").move_to(caption1)
        i_squared_long = MathTex(r"I^2 = \left( \int_{-\infty}^{\infty} e^{-x^2} dx \right) \left( \int_{-\infty}^{\infty} e^{-y^2} dy \right)")
        self.play(ReplacementTransform(caption1, caption2))
        self.play(ReplacementTransform(gaussian_integral, i_squared_long))
        self.wait(2)
        
        double_integral = MathTex(r"I^2 = \int_{-\infty}^{\infty} \int_{-\infty}^{\infty} e^{-(", r"x^2+y^2", r")} \,dx\,dy").scale(1.1)
        self.play(ReplacementTransform(i_squared_long, double_integral))
        self.wait(2)

        # 4. Visualize the switch to polar coordinates
        caption3 = Text("This is the volume under a 2D bell curve.").move_to(caption2)
        axes = Axes(x_range=[-3, 3, 1], y_range=[-3, 3, 1], x_length=6, y_length=6)
        circles = VGroup(*[
            Circle(radius=r, stroke_opacity=1 - r/3.5, color=BLUE) 
            for r in np.arange(0.25, 3.25, 0.25)
        ])
        
        self.play(
            ReplacementTransform(caption2, caption3),
            double_integral.animate.to_edge(UP, buff=1.5)
        )
        self.play(Create(axes), FadeIn(circles, run_time=2))
        self.wait(2)

        caption4 = Text("Switching to polar coordinates makes it easy.").move_to(caption3)
        self.play(ReplacementTransform(caption3, caption4))

        # Highlight x^2+y^2 and show its polar equivalent
        x2y2_part = double_integral.get_part_by_tex("x^2+y^2")
        highlight_box = SurroundingRectangle(x2y2_part, color=YELLOW)
        polar_relation = MathTex(r"x^2 + y^2 = r^2").next_to(axes, UP, buff=0.2)
        self.play(Create(highlight_box))
        self.wait(1)
        self.play(Transform(highlight_box, polar_relation))
        self.wait(1)

        # Explain the area element dA = r dr d(theta)
        area_caption = Text("The area element dA also changes.", font_size=28).next_to(caption4, DOWN)
        cartesian_rect = Rectangle(width=0.4, height=0.3, fill_color=YELLOW, fill_opacity=0.5).move_to(axes.c2p(1.5, 1))
        cartesian_label = MathTex(r"dx\,dy").next_to(cartesian_rect, UR, buff=0.1).scale(0.7)
        polar_wedge = AnnularSector(inner_radius=1.5, outer_radius=1.8, start_angle=30*DEGREES, angle=15*DEGREES, fill_color=ORANGE, fill_opacity=0.5)
        polar_label = MathTex(r"r\,dr\,d\theta").next_to(polar_wedge, UR, buff=0.1).scale(0.7)

        self.play(FadeOut(circles), FadeOut(highlight_box), FadeOut(polar_relation))
        self.play(Write(area_caption))
        self.play(Create(cartesian_rect), Write(cartesian_label))
        self.wait(1.5)
        self.play(ReplacementTransform(cartesian_rect, polar_wedge), ReplacementTransform(cartesian_label, polar_label))
        self.wait(2)
        self.play(FadeOut(area_caption, polar_wedge, polar_label, axes))

        # 5. Transform the integral and solve it
        polar_integral = MathTex(r"I^2 = \int_{0}^{2\pi} \left( \int_{0}^{\infty} e^{-r^2} r\,dr \right) d\theta").move_to(ORIGIN).scale(1.1)
        self.play(FadeOut(caption4), ReplacementTransform(double_integral, polar_integral))
        self.wait(2)
        
        # Solve the inner integral
        inner_integral_part = polar_integral[0][7:18]
        inner_integral_box = SurroundingRectangle(inner_integral_part, color=YELLOW)
        self.play(Create(inner_integral_box))
        self.wait(1)

        inner_calc = MathTex(r"\int_{0}^{\infty} e^{-r^2} r\,dr = \left[ -\frac{1}{2} e^{-r^2} \right]_{0}^{\infty} = \frac{1}{2}")
        inner_calc.next_to(polar_integral, DOWN, buff=0.75)
        self.play(Write(inner_calc))
        self.wait(3)

        # Substitute result back into the main integral
        integral_solved_inner = MathTex(r"I^2 = \int_{0}^{2\pi} \frac{1}{2} \,d\theta").move_to(polar_integral).scale(1.1)
        self.play(
            FadeOut(inner_integral_box, inner_calc),
            Transform(polar_integral, integral_solved_inner)
        )
        self.wait(2)

        # Solve the final integral
        i_squared_pi = MathTex(r"I^2 = \pi").scale(1.5).move_to(polar_integral)
        self.play(Transform(polar_integral, i_squared_pi))
        self.wait(2)

        # 6. Conclusion
        final_caption = Text("So the original integral is the square root of π.").to_edge(UP)
        i_sqrt_pi = MathTex(r"I = \int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}").scale(1.2)
        self.play(Write(final_caption))
        self.play(ReplacementTransform(polar_integral, i_sqrt_pi))
        self.wait(3)

        self.play(
            FadeOut(i_sqrt_pi, shift=DOWN),
            FadeOut(final_caption, shift=UP)
        )
        self.wait(1)