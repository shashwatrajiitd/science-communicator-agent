from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class ExponentiationAsRotationBTheRotatingPoint(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Initial state from previous scene to ensure continuity
        i_symbol = MathTex(r"i", font_size=72)
        i_definition = MathTex(r"i^2 = -1", font_size=36).next_to(i_symbol, RIGHT, buff=0.3)
        i_group = VGroup(i_symbol, i_definition).move_to(ORIGIN)
        self.add(i_group)

        # Beat 1: Introduce e^(ix) and the complex plane
        with self.voiceover(text="When you take 'e' to the power of 'i' times some number 'x', the result isn't a bigger number.") as tracker:
            formula = MathTex(r"e^{ix}", font_size=42).to_edge(UP, buff=0.5)
            
            # Shared object: complex_plane
            axes = Axes(
                x_range=[-1.5, 1.5, 1],
                y_range=[-1.5, 1.5, 1],
                x_length=6,
                y_length=6,
                axis_config={"color": GREY},
                x_axis_config={"numbers_to_include": [-1, 1]},
                y_axis_config={"numbers_to_include": [-1, 1]}
            )
            x_label = axes.get_x_axis_label(Text("Real", font_size=28, color=GREY))
            y_label = axes.get_y_axis_label(Text("Imaginary", font_size=28, color=GREY).rotate(90 * DEGREES))
            complex_plane = VGroup(axes, x_label, y_label)

            # Shared object: unit_circle
            unit_circle = Circle(
                radius=axes.x_axis.n2p(1)[0], 
                color=WHITE
            ).move_to(axes.c2p(0, 0))

            self.play(
                FadeOut(i_group),
                Write(formula),
                Create(complex_plane),
                Create(unit_circle),
                run_time=tracker.duration
            )

        # Beat 2: Introduce the rotating point and radius
        with self.voiceover(text="Instead, it's a point that rotates around a circle of radius one.") as tracker:
            # Shared object: rotating_point
            rotating_point = Dot(
                point=axes.c2p(1, 0),
                radius=0.05,
                color=YELLOW
            )
            
            # Shared object: radius_line
            radius_line = Line(
                start=axes.c2p(0, 0),
                end=rotating_point.get_center(),
                color=YELLOW
            )

            self.play(
                Create(rotating_point),
                Create(radius_line),
                run_time=tracker.duration
            )

        # Beat 3: Animate the rotation with 'x'
        with self.voiceover(text="The number 'x' is simply the distance it travels along the circle's edge.") as tracker:
            x_val = ValueTracker(0)

            rotating_point.add_updater(
                lambda mob: mob.move_to(axes.c2p(np.cos(x_val.get_value()), np.sin(x_val.get_value())))
            )
            radius_line.add_updater(
                lambda mob: mob.put_start_and_end_on(axes.c2p(0, 0), rotating_point.get_center())
            )

            # Shared object: angle_arc
            angle_arc = Arc(
                radius=0.3,
                start_angle=0,
                angle=x_val.get_value(),
                color=BLUE
            ).move_to(axes.c2p(0,0))
            angle_arc.add_updater(
                lambda mob: mob.become(
                    Arc(
                        radius=0.3,
                        start_angle=0,
                        angle=x_val.get_value(),
                        color=BLUE
                    ).move_to(axes.c2p(0,0))
                )
            )

            arc_label = MathTex("x", font_size=28, color=BLUE)
            arc_label.add_updater(
                lambda mob: mob.move_to(
                    axes.c2p(0,0) + 
                    np.array([0.45 * np.cos(x_val.get_value() / 2), 0.45 * np.sin(x_val.get_value() / 2), 0])
                )
            )
            
            self.add(angle_arc, arc_label)

            self.play(
                x_val.animate.set_value(2 * PI),
                run_time=tracker.duration,
                rate_func=linear
            )
            
            # Clean up updaters for the next scene
            rotating_point.clear_updaters()
            radius_line.clear_updaters()
            angle_arc.clear_updaters()
            arc_label.clear_updaters()
