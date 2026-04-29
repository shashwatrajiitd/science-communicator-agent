from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class IntroducingTheZetaFunction(ThreeDScene, VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Start with the question from the previous scene for continuity.
        initial_question = Text("Is there a pattern?", font_size=36)
        self.add(initial_question)

        # This function defines the shape of our landscape. It's a visual
        # representation, not the mathematically exact Riemann Zeta function.
        def zeta_landscape_func(u, v):
            # A combination of waves to create an interesting, complex surface.
            val = np.sin(u) + 0.5 * np.sin(v*2) + 0.3 * np.cos(u*v*0.5)
            return np.array([u, v, val])

        with self.voiceover(text="To find this pattern, mathematicians use a special tool: the Riemann Zeta function.") as tracker:
            formula = MathTex(r"\zeta(s) = \sum_{n=1}^{\infty} \frac{1}{n^s}", font_size=42)
            formula.to_edge(UP, buff=0.3)

            surface = Surface(
                zeta_landscape_func,
                u_range=[-4, 4],
                v_range=[-4, 4],
                resolution=(42, 42),
                fill_opacity=0.9,
            ).scale(1.5) # Scale to be visually impressive
            surface.set_color_by_gradient(BLUE, TEAL, GREEN)

            self.play(
                FadeOut(initial_question, shift=DOWN),
                Write(formula),
                run_time=tracker.duration * 0.4
            )
            self.set_camera_orientation(phi=70 * DEGREES, theta=-45 * DEGREES, zoom=0.9)
            self.play(Create(surface), run_time=tracker.duration * 0.6)

        with self.voiceover(text="Think of it as a landscape. For every point 's' on a flat map, the function gives you a height.") as tracker:
            # The 'flat map' is the complex plane.
            # NOTE: We use a square portion of the plane for visual clarity in the portrait aspect ratio.
            # The key visual properties (labels, color) match the shared object spec.
            plane = Axes(
                x_range=[-4, 4, 1], y_range=[-4, 4, 1],
                x_length=4, y_length=4,
                axis_config={"color": GREY, "include_tip": False}
            )
            x_label = plane.get_x_axis_label(Text("Real", font_size=24))
            y_label = plane.get_y_axis_label(Text("Imaginary", font_size=24).rotate(PI/2), direction=LEFT, buff=0.3)
            complex_plane = VGroup(plane, x_label, y_label)

            s_dot = Dot3D(point=plane.c2p(1.5, 1.5), color=YELLOW, radius=0.08)
            s_label = MathTex("s", font_size=32).next_to(s_dot, OUT + UR, buff=0.1)
            
            line = Line(s_dot.get_center(), s_dot.get_center() + OUT, color=RED)

            s_label.add_updater(lambda m: m.next_to(s_dot, OUT + UR, buff=0.1))
            line.add_updater(
                lambda l: l.put_start_and_end_on(
                    s_dot.get_center(),
                    zeta_landscape_func(
                        s_dot.get_center()[0] * (8/4), # u = x_world * (x_range_span / x_length)
                        s_dot.get_center()[1] * (8/4)  # v = y_world * (y_range_span / y_length)
                    ) * 1.5 # Apply same scale as surface
                )
            )

            self.play(Create(complex_plane), run_time=tracker.duration * 0.3)
            self.play(FadeIn(s_dot), Write(s_label), Create(line), run_time=tracker.duration * 0.2)
            
            path = Arc(radius=2, start_angle=PI/4, angle=-(3*PI/2), arc_center=ORIGIN)
            self.play(MoveAlongPath(s_dot, path), run_time=tracker.duration * 0.5)

            s_label.clear_updaters()
            line.clear_updaters()

        with self.voiceover(text="The most important places on this landscape are the 'zeros' - the points where the height is exactly zero.") as tracker:
            # We place dots on the plane to represent the zeros.
            zeros = VGroup(
                Dot(plane.c2p(-PI/2, 0), color=ORANGE, radius=0.1),
                Dot(plane.c2p(PI/2, PI), color=ORANGE, radius=0.1),
                Dot(plane.c2p(-PI, PI/2), color=ORANGE, radius=0.1),
                Dot(plane.c2p(0, -PI), color=ORANGE, radius=0.1)
            )
            
            self.play(
                surface.animate.set_fill_opacity(0.2),
                FadeOut(s_dot, s_label, line),
                run_time=tracker.duration * 0.5
            )
            self.play(
                LaggedStart(*[GrowFromCenter(z) for z in zeros]),
                run_time=tracker.duration * 0.5
            )
        
        self.wait(1)