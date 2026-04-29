from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
import numpy as np

class PiInTheNormalDistribution(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en", tld="com"))

        # ZONES
        title_zone = lambda mob: mob.to_edge(UP, buff=0.5)
        caption_zone = lambda mob: mob.to_edge(DOWN, buff=0.5)
        center_zone = lambda mob: mob.move_to(ORIGIN)

        # TITLE
        title = Tex("The Normal Distribution", font_size=42).move_to(title_zone(VGroup()))
        
        # Initial Formula
        normal_dist_formula = MathTex(
            r"f(x) = \frac{1}{\sigma \sqrt{2\pi}} e^{-\frac{1}{2} \left( \frac{x-\mu}{\sigma} \right)^2}",
            font_size=36
        ).move_to(center_zone(VGroup()))
        
        caption1_text = "The formula for the normal distribution, or bell curve, is fundamental in statistics."
        caption1 = Text(caption1_text, font_size=28).move_to(caption_zone(VGroup()))

        with self.voiceover(text=caption1_text) as tracker:
            self.play(Write(title), Write(normal_dist_formula), FadeIn(caption1, shift=UP), run_time=tracker.duration)

        pi_part = normal_dist_formula.get_part_by_tex(r"\pi")
        
        caption2_text = "But have you ever wondered why pi, a number from geometry, shows up here?"
        caption2 = Text(caption2_text, font_size=28).move_to(caption_zone(VGroup()))

        with self.voiceover(text=caption2_text) as tracker:
            self.play(
                Circumscribe(pi_part, color=YELLOW, fade_out=True),
                Transform(caption1, caption2),
                run_time=tracker.duration
            )
        
        # Simplify the problem
        simplified_integral = MathTex(r"I = \int_{-\infty}^{\infty} e^{-x^2} dx", font_size=36).move_to(center_zone(VGroup()))

        caption3_text = "The key lies in a famous problem called the Gaussian integral. Solving this is the heart of the matter."
        caption3 = Text(caption3_text, font_size=28).move_to(caption_zone(VGroup()))

        with self.voiceover(text=caption3_text) as tracker:
            self.play(
                FadeOut(title),
                TransformMatchingTex(normal_dist_formula, simplified_integral),
                Transform(caption1, caption3),
                run_time=tracker.duration
            )

        # The trick: squaring the integral
        integral_squared = MathTex(r"I^2 = \left( \int_{-\infty}^{\infty} e^{-x^2} dx \right) \left( \int_{-\infty}^{\infty} e^{-y^2} dy \right)", font_size=36).move_to(center_zone(VGroup()))
        
        caption4_text = "This integral is tricky to solve in one dimension. The brilliant insight is to square it."
        caption4 = Text(caption4_text, font_size=28).move_to(caption_zone(VGroup()))

        with self.voiceover(text=caption4_text) as tracker:
            self.play(
                TransformMatchingTex(simplified_integral, integral_squared),
                Transform(caption1, caption4),
                run_time=tracker.duration
            )

        # Combine into a 2D integral
        double_integral = MathTex(r"I^2 = \int_{-\infty}^{\infty} \int_{-\infty}^{\infty} e^{-(x^2+y^2)} \,dx\,dy", font_size=36).move_to(center_zone(VGroup()))
        
        caption5_text = "By treating x and y as independent variables, we can combine this into a double integral over a 2D plane."
        caption5 = Text(caption5_text, font_size=28).move_to(caption_zone(VGroup()))

        with self.voiceover(text=caption5_text) as tracker:
            self.play(
                TransformMatchingTex(integral_squared, double_integral),
                Transform(caption1, caption5),
                run_time=tracker.duration
            )
        
        # Cleanup before 3D
        self.play(FadeOut(double_integral), FadeOut(caption1))

        # Visualize in 3D
        axes = ThreeDAxes(
            x_range=[-3, 3, 1], y_range=[-3, 3, 1], z_range=[0, 1, 0.5],
            x_length=6, y_length=6, z_length=3
        )
        surface = Surface(
            lambda u, v: axes.c2p(u, v, np.exp(-(u**2 + v**2))),
            u_range=[-3, 3], v_range=[-3, 3],
            resolution=(42, 42),
            fill_opacity=0.7
        )
        surface.set_fill_by_value(axes=axes, colorscale=[(BLUE, -1), (GREEN, 0), (YELLOW, 1)])
        
        caption6_text = "This integral represents the volume under a 3D surface, a beautiful bell-shaped hill."
        caption6 = Text(caption6_text, font_size=28).move_to(caption_zone(VGroup()))

        with self.voiceover(text=caption6_text) as tracker:
            self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)
            self.play(Create(axes), Create(surface), FadeIn(caption6, shift=UP), run_time=tracker.duration)

        caption7_text = "Notice its perfect circular symmetry. This suggests a change of coordinates might simplify things."
        caption7 = Text(caption7_text, font_size=28).move_to(caption_zone(VGroup()))

        with self.voiceover(text=caption7_text) as tracker:
            self.move_camera(theta=120 * DEGREES, run_time=tracker.duration)
            self.play(Transform(caption6, caption7))

        # Cleanup 3D
        current_group = VGroup(axes, surface, caption6)
        self.play(FadeOut(current_group))
        self.move_camera(phi=0, theta=-90*DEGREES) # Reset camera

        # Transform to polar coordinates
        polar_title = Tex("A Change of Perspective", font_size=42).move_to(title_zone(VGroup()))
        cartesian_eq = MathTex(r"I^2 = \int \int e^{-(", r"x^2+y^2", r")} \,", r"dx\,dy", font_size=36).move_to(center_zone(VGroup()))
        
        caption8_text = "Let's switch from Cartesian coordinates (x, y) to polar coordinates (r, theta)."
        caption8 = Text(caption8_text, font_size=28).move_to(caption_zone(VGroup()))

        with self.voiceover(text=caption8_text) as tracker:
            self.play(Write(polar_title), Write(cartesian_eq), FadeIn(caption8, shift=UP), run_time=tracker.duration)

        polar_eq = MathTex(r"I^2 = \int_{0}^{2\pi} \int_{0}^{\infty} e^{-", r"r^2", r"} \,", r"r\,dr\,d\theta", font_size=36).move_to(center_zone(VGroup()))
        
        caption9_text_line1 = Text("The term x squared plus y squared becomes r squared.", font_size=28)
        caption9_text_line2 = Text("And the area element dx dy becomes r dr d-theta.", font_size=28)
        caption9 = VGroup(caption9_text_line1, caption9_text_line2).arrange(DOWN, buff=0.15).move_to(caption_zone(VGroup()))
        
        with self.voiceover(text="The term x-squared plus y-squared becomes r-squared, and the area element dx dy becomes r dr d-theta.") as tracker:
            self.play(
                TransformMatchingTex(cartesian_eq, polar_eq, transform_mismatched_part=True),
                Transform(caption8, caption9),
                run_time=tracker.duration
            )

        # Solving the integral
        inner_integral = polar_eq.get_part_by_tex(r"\int_{0}^{\infty} e^{-r^2} \,r\,dr")
        outer_integral = polar_eq.get_part_by_tex(r"\int_{0}^{2\pi}")
        d_theta = polar_eq.get_part_by_tex(r"d\theta")
        
        caption10_text = "This looks more complex, but it's much easier to solve. Let's start with the inner integral."
        caption10 = Text(caption10_text, font_size=28).move_to(caption_zone(VGroup()))

        with self.voiceover(text=caption10_text) as tracker:
            self.play(
                Circumscribe(inner_integral, color=YELLOW),
                Transform(caption8, caption10),
                run_time=tracker.duration
            )
        
        # Result of inner integral
        solved_inner = MathTex(r"I^2 = \int_{0}^{2\pi}", r"\left( \frac{1}{2} \right)", r"d\theta", font_size=36).move_to(center_zone(VGroup()))
        
        caption11_text = "The integral of r times e to the minus r-squared evaluates to exactly one half."
        caption11 = Text(caption11_text, font_size=28).move_to(caption_zone(VGroup()))
        
        with self.voiceover(text=caption11_text) as tracker:
            # Manually align parts for a smooth transform
            group1 = VGroup(outer_integral.copy(), inner_integral.copy(), d_theta.copy())
            group2 = VGroup(solved_inner.get_part_by_tex(r"\int_{0}^{2\pi}"), solved_inner.get_part_by_tex(r"\left( \frac{1}{2} \right)"), solved_inner.get_part_by_tex(r"d\theta"))
            self.play(
                FadeOut(polar_eq),
                FadeIn(solved_inner),
                Transform(caption8, caption11),
                run_time=tracker.duration
            )
        
        # Final result
        pi_result = MathTex(r"I^2 = \pi", font_size=42).move_to(center_zone(VGroup()))
        
        caption12_text = "And now, integrating a constant one-half from 0 to 2 pi gives us... pi!"
        caption12 = Text(caption12_text, font_size=28).move_to(caption_zone(VGroup()))

        with self.voiceover(text=caption12_text) as tracker:
            self.play(
                TransformMatchingTex(solved_inner, pi_result),
                Transform(caption8, caption12),
                run_time=tracker.duration
            )

        final_answer = MathTex(r"I = \sqrt{\pi}", font_size=42).move_to(center_zone(VGroup()))
        
        caption13_text_line1 = Text("So, the original Gaussian integral equals the square root of pi.", font_size=28)
        caption13_text_line2 = Text("This is where the pi in the normal distribution is born.", font_size=28)
        caption13 = VGroup(caption13_text_line1, caption13_text_line2).arrange(DOWN, buff=0.15).move_to(caption_zone(VGroup()))

        with self.voiceover(text="So, the original Gaussian integral equals the square root of pi. This is where the pi in the normal distribution is born.") as tracker:
            self.play(
                TransformMatchingTex(pi_result, final_answer),
                Transform(caption8, caption13),
                run_time=tracker.duration
            )

        caption14_text = "By transforming a 1D problem into 2D, a hidden circular symmetry revealed itself, and pi naturally emerged."
        caption14 = Text(caption14_text, font_size=28, line_spacing=1.2).move_to(caption_zone(VGroup()))
        
        with self.voiceover(text=caption14_text) as tracker:
            self.play(
                Indicate(final_answer, scale_factor=1.2, color=YELLOW),
                Transform(caption8, caption14),
                run_time=tracker.duration
            )

        self.wait(2)
        # Final fade out
        self.play(FadeOut(VGroup(*self.mobjects)))
        self.wait(1)