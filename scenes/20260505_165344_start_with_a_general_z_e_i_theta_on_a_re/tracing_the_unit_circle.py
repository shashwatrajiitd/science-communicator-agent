from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TracingTheUnitCircle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Layout zones
        title_zone = UP * 3.5
        center_zone = ORIGIN

        # Initial state from previous scene
        axes = Axes(
            x_range=[-1.5, 1.5, 1], y_range=[-1.5, 1.5, 1],
            x_length=4, y_length=4, axis_config={"color": GREY},
            x_axis_config={"numbers_to_include": [-1, 1]},
            y_axis_config={"numbers_to_include": [-1, 1]},
        ).move_to(center_zone)
        x_label = axes.get_x_axis_label(Tex("Real", font_size=28, color=GREY), edge=RIGHT, direction=RIGHT, buff=0.2)
        y_label = axes.get_y_axis_label(Tex("Imaginary", font_size=28, color=GREY), edge=UP, direction=UP, buff=0.2)
        origin_label = Tex("0", font_size=28, color=GREY).next_to(axes.c2p(0, 0), DR, buff=0.1)
        complex_plane = VGroup(axes, x_label, y_label, origin_label)
        formula = MathTex(r"z = e^{i\theta}", font_size=42).move_to(title_zone)

        theta_tracker = ValueTracker(PI / 4)

        z_dot = Dot(color=YELLOW)
        z_label = MathTex(r"z", font_size=36, color=YELLOW)
        moving_point_z = VGroup(z_dot, z_label)
        def update_z_group(mob):
            theta = theta_tracker.get_value()
            point = axes.c2p(np.cos(theta), np.sin(theta))
            mob[0].move_to(point)
            mob[1].next_to(mob[0], UR, buff=0.1)
        moving_point_z.add_updater(update_z_group)
        
        self.add(complex_plane, formula, moving_point_z)
        update_z_group(moving_point_z)

        # Beat 1
        with self.voiceover(text="Let's start theta at zero. Here, z equals one, sitting on the real axis.") as tracker:
            radius_line = Line(axes.c2p(0,0), z_dot.get_center(), color=WHITE, stroke_width=2)
            radius_line.add_updater(lambda mob: mob.put_start_and_end_on(axes.c2p(0,0), z_dot.get_center()))

            angle_arc = Arc(radius=0.4, angle=theta_tracker.get_value(), color=WHITE, arc_center=axes.c2p(0,0))
            angle_arc.add_updater(lambda mob: mob.become(Arc(radius=0.4, angle=theta_tracker.get_value(), color=WHITE, arc_center=axes.c2p(0,0))))
            
            angle_label = MathTex(r"\theta = 0", font_size=32)
            angle_label.add_updater(lambda mob: mob.move_to(
                axes.c2p(0.6 * np.cos(theta_tracker.get_value() / 2), 0.6 * np.sin(theta_tracker.get_value() / 2))
            ))

            self.play(
                theta_tracker.animate.set_value(0.0001),
                Create(radius_line),
                Create(angle_arc),
                FadeIn(angle_label),
                run_time=tracker.duration
            )

        # Combine beats 2 and 3 for a single, constant-speed animation
        combined_text = "As we increase theta, the point z moves, always keeping a distance of one from the origin. By the time theta reaches two pi, we've traced a perfect circle and returned right back where we started."

        with self.voiceover(text=combined_text) as tracker:
            traced_path = TracedPath(z_dot.get_center, stroke_color=BLUE, stroke_width=5)
            self.add(traced_path)
            
            # Change label to just "theta" and let it follow the arc
            angle_label_theta = MathTex(r"\theta", font_size=32).move_to(angle_label.get_center())
            self.play(Transform(angle_label, angle_label_theta), run_time=0.5)
            
            # The updater from the original angle_label is lost in Transform. Re-add it.
            angle_label.add_updater(lambda mob: mob.move_to(
                axes.c2p(0.6 * np.cos(theta_tracker.get_value() / 2), 0.6 * np.sin(theta_tracker.get_value() / 2))
            ))

            # Estimate duration of the first sentence to time the final label transform
            # The two sentences are of similar length, so we'll start the final transform
            # a bit after the halfway point of the total narration.
            wait_duration = tracker.duration * 0.55
            transform_duration = tracker.duration - wait_duration

            # Create the final label that we will transform into
            final_angle_label = MathTex(r"\theta = 2\pi", font_size=32).move_to(axes.c2p(0.6, 0.2))

            # Define the final label transform animation
            def transform_label_at_end(mob):
                mob.clear_updaters()
                return Transform(mob, final_angle_label)

            # Play rotation and the delayed label transform together
            self.play(
                theta_tracker.animate(rate_func=linear).set_value(2 * PI),
                Succession(
                    Wait(wait_duration),
                    AnimationGroup(transform_label_at_end(angle_label), run_time=transform_duration)
                ),
                run_time=tracker.duration - 0.5
            )

        self.wait(1)
