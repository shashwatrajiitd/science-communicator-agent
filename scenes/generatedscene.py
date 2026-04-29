from manim import *
import numpy as np

class PiInNormalDistribution(ThreeDScene):
    def construct(self):
        # Colors
        PI_COLOR = GOLD
        CURVE_COLOR = BLUE
        AREA_COLOR = BLUE_E
        SURFACE_COLOR = BLUE_E

        # Helper for captions
        def show_caption(text, wait_time=2.5, scale=0.7):
            caption = Text(text, font_size=36).to_edge(DOWN, buff=0.5)
            self.play(FadeIn(caption, shift=UP))
            self.wait(wait_time)
            self.play(FadeOut(caption, shift=UP))
            return caption

        # 1. Introduction: The formula and the question
        title_formula = MathTex(
            r"\phi(x) = \frac{1}{\sqrt{2\pi}} e^{-\frac{x^2}{2}}",
            font_size=60
        ).to_edge(UP, buff=1)
        
        show_caption("The Normal Distribution is one of the most important in statistics.")
        self.play(Write(title_formula))
        self.wait()

        pi_part = title_formula.get_part_by_tex(r"\pi")
        self.play(Indicate(pi_part, color=PI_COLOR, scale_factor=1.5))
        show_caption("But why does \(\pi\), from circles, appear in its formula?")
        self.play(FadeOut(title_formula))

        # 2. The Area must be 1
        integral_goal = MathTex(r"\text{Total Probability} = \int_{-\infty}^{\infty} \phi(x) \, dx = 1", font_size=48).to_edge(UP)
        self.play(Write(integral_goal))
        show_caption("For any probability distribution, the total area under its curve must be 1.")

        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[0, 0.5, 0.1],
            x_length=10,
            y_length=4,
            axis_config={"include_tip": False},
        ).center().shift(DOWN*0.5)
        
        curve = axes.plot(lambda x: np.exp(-x**2 / 2) / np.sqrt(2*np.pi), color=CURVE_COLOR)
        area = axes.get_area(curve, x_range=[-4, 4], color=AREA_COLOR, opacity=0.8)
        
        self.play(Create(axes), Create(curve))
        self.play(FadeIn(area))
        self.wait(2)

        # 3. Simplify the problem
        self.play(FadeOut(axes, curve, area))
        show_caption("To understand the \(\pi\), let's look at the core of this integral.")

        new_integral = MathTex(r"I = \int_{-\infty}^{\infty} e^{-x^2} dx", font_size=60).to_corner(UL)
        self.play(Transform(integral_goal, new_integral))
        self.wait(1)

        show_caption("The trick is to not solve this integral, but to solve its square.")

        I_squared = MathTex(r"I^2 = \left( \int_{-\infty}^{\infty} e^{-x^2} dx \right) \left( \int_{-\infty}^{\infty} e^{-y^2} dy \right)", font_size=48).next_to(new_integral, DOWN, buff=0.5)
        self.play(Write(I_squared))
        self.wait(2)

        double_integral = MathTex(r"I^2 = \int_{-\infty}^{\infty} \int_{-\infty}^{\infty} e^{-(x^2+y^2)} \,dx\,dy", font_size=48).move_to(I_squared)
        self.play(ReplacementTransform(I_squared, double_integral))

        show_caption("This expression represents the volume under a 2D Gaussian surface.")
        self.play(FadeOut(integral_goal, double_integral))

        # 4. Switch to 3D and visualize the volume
        axes_3d = ThreeDAxes(x_range=[-3,3], y_range=[-3,3], z_range=[0,2], x_length=8, y_length=8, z_length=4)
        surface = Surface(
            lambda u, v: axes_3d.c2p(u, v, np.exp(-(u**2 + v**2))),
            u_range=[-2.5, 2.5],
            v_range=[-2.5, 2.5],
            resolution=(32, 32),
            fill_opacity=0.7,
            checkerboard_colors=[SURFACE_COLOR, BLUE_D]
        )

        self.set_camera_orientation(phi=75 * DEGREES, theta=-120 * DEGREES)
        self.play(Create(axes_3d), Create(surface))
        self.wait(1)

        show_caption("This 'hill' has perfect rotational symmetry.", wait_time=3)
        self.begin_ambient_camera_rotation(rate=0.15)
        self.wait(3)
        self.stop_ambient_camera_rotation()

        # 5. The switch to polar coordinates
        show_caption("This symmetry is key. Let's switch to polar coordinates.")

        polar_eqs = VGroup(
            MathTex(r"x^2+y^2 = r^2"),
            MathTex(r"dx\,dy = r\,dr\,d\theta")
        ).arrange(DOWN, buff=0.4).to_corner(UR)
        
        self.add_fixed_in_frame_mobjects(polar_eqs)
        self.play(Write(polar_eqs))
        self.wait(2)

        show_caption("Our volume integral transforms into this:", wait_time=3)
        polar_integral = MathTex(r"I^2 = \int_0^{2\pi} \int_0^{\infty} e^{-r^2} r \,dr\,d\theta", font_size=48).to_corner(UL)
        self.add_fixed_in_frame_mobjects(polar_integral)
        self.play(Write(polar_integral))
        self.wait(2)

        # 6. Solving the integral
        show_caption("And this new integral is surprisingly easy to solve!")
        
        # Animate inner part
        inner_integral = polar_integral.get_parts_by_tex(r"\int_0^{\infty}")
        self.play(Indicate(inner_integral, color=YELLOW, scale_factor=1.1))
        
        inner_solve = MathTex(r"\int_0^{\infty} e^{-r^2} r \,dr = \frac{1}{2}", font_size=42).next_to(polar_integral, DOWN, buff=0.5)
        self.add_fixed_in_frame_mobjects(inner_solve)
        self.play(Write(inner_solve))
        self.wait(2)

        # Animate outer part
        outer_integral = MathTex(r"I^2 = \int_0^{2\pi} \frac{1}{2} \,d\theta", font_size=48).move_to(polar_integral)
        self.add_fixed_in_frame_mobjects(outer_integral)
        self.play(ReplacementTransform(polar_integral, outer_integral), FadeOut(inner_solve))
        self.wait(1.5)

        pi_result = MathTex(r"I^2 = \frac{1}{2} \cdot (2\pi) = \pi", font_size=60).move_to(ORIGIN)
        pi_result.set_color_by_tex(r"\pi", PI_COLOR)
        self.add_fixed_in_frame_mobjects(pi_result)
        self.play(Transform(outer_integral, pi_result), FadeOut(polar_eqs))
        self.wait(2)

        # 7. Conclusion
        self.play(FadeOut(axes_3d, surface))

        final_result = MathTex(r"I = \int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}", font_size=60).move_to(pi_result)
        final_result.set_color_by_tex(r"\pi", PI_COLOR)
        self.play(ReplacementTransform(outer_integral, final_result))

        show_caption("The integral we needed was \(\sqrt{\pi}\).", wait_time=3)
        self.play(final_result.animate.to_edge(UP))

        back_to_normal = MathTex(r"\int_{-\infty}^{\infty} e^{-x^2/2} dx = \sqrt{2\pi}", font_size=48).next_to(final_result, DOWN, buff=0.7)
        back_to_normal.set_color_by_tex(r"\pi", PI_COLOR)
        self.play(Write(back_to_normal))
        self.wait(2)

        final_caption_1 = Text("So, to make the total area 1, we must divide by this value.", font_size=36).to_edge(DOWN)
        final_formula = MathTex(r"\phi(x) = \frac{1}{\sqrt{2\pi}} e^{-\frac{x^2}{2}}", font_size=60).center()
        final_formula.set_color_by_tex(r"\pi", PI_COLOR)
        self.play(FadeIn(final_caption_1))
        self.play(FadeOut(final_result, back_to_normal), FadeIn(final_formula))
        self.wait(3)

        final_caption_2 = Text("Pi is there because of the rotational symmetry hiding in the math.", font_size=36).to_edge(DOWN)
        self.play(ReplacementTransform(final_caption_1, final_caption_2))
        self.wait(4)