from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class RuleThreeChangeCreatesSwirls(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Helper function from the previous scene to ensure perfect visual continuity.
        def create_magnet_with_fields(position, height, width):
            magnet_center = position
            north_rect = Rectangle(height=height/2, width=width, fill_color=RED, fill_opacity=1, stroke_width=0)
            south_rect = Rectangle(height=height/2, width=width, fill_color=BLUE, fill_opacity=1, stroke_width=0)
            magnet_body = VGroup(north_rect, south_rect).arrange(DOWN, buff=0).move_to(magnet_center)
            
            north_pole_top = magnet_body.get_top()
            south_pole_bottom = magnet_body.get_bottom()
            
            label_n = Tex("N", font_size=42).next_to(north_rect, UP, buff=0.2)
            label_s = Tex("S", font_size=42).next_to(south_rect, DOWN, buff=0.2)
            
            magnet_group = VGroup(magnet_body, label_n, label_s)

            field_lines = VGroup()
            line_internal = Line(south_pole_bottom + UP * 0.1, north_pole_top + DOWN * 0.1, color=TEAL, stroke_width=3)
            field_lines.add(line_internal)

            for scale_factor in [0.7, 1.0]:
                arc_path_right = ArcBetweenPoints(north_pole_top, south_pole_bottom, angle=-PI * 0.8)
                arc_path_left = ArcBetweenPoints(north_pole_top, south_pole_bottom, angle=PI * 0.8)
                
                arc_right = arc_path_right.scale(scale_factor, about_point=magnet_center).set_color(TEAL).set_stroke(width=3)
                arc_left = arc_path_left.scale(scale_factor, about_point=magnet_center).set_color(TEAL).set_stroke(width=3)
                
                arc_right.add_tip(tip_length=0.2)
                arc_left.add_tip(tip_length=0.2)
                
                field_lines.add(arc_right, arc_left)
            
            return VGroup(magnet_group, field_lines)

        # Recreate the final state of the previous scene for a continuous cut.
        top_magnet_and_fields = create_magnet_with_fields(UP * 2.0, 2.0, 0.8)
        bottom_magnet_and_fields = create_magnet_with_fields(DOWN * 2.0, 2.0, 0.8)
        initial_magnets = VGroup(top_magnet_and_fields, bottom_magnet_and_fields)
        self.add(initial_magnets)
        self.wait(0.2)

        title = Text("Rule 3: Faraday's Law", font_size=36).to_edge(UP, buff=0.3)
        b_field_visual = Cross(stroke_color=TEAL, stroke_width=8).scale(0.5)
        b_label = MathTex(r"\vec{B}", font_size=42, color=TEAL).next_to(b_field_visual, DR, buff=0.2)
        b_field = VGroup(b_field_visual, b_label).move_to(ORIGIN)

        with self.voiceover(text="Now for the interesting parts. Rule three: A changing magnetic field creates an electric field.") as tracker:
            self.play(
                FadeOut(initial_magnets, shift=DOWN),
                FadeIn(title, shift=UP),
                run_time=1.5
            )
            # Shorten the creation time to reduce the static period before the change.
            self.play(
                Create(b_field),
                run_time=max(0.1, tracker.duration - 1.5)
            )

        with self.voiceover(text="But not a straight one like from a charge. It creates a swirling, circular electric field around the changing magnetic field.") as tracker:
            radius = 1.2
            e_arrows = VGroup()
            num_arrows = 8
            arrow_length = 0.5
            for i in range(num_arrows):
                angle = i * TAU / num_arrows
                pos = np.array([radius * np.cos(angle), radius * np.sin(angle), 0])
                tangent_dir = np.array([-np.sin(angle), np.cos(angle), 0]) # Counter-clockwise
                
                arrow_center = pos
                arrow_start = arrow_center - tangent_dir * arrow_length / 2
                arrow_end = arrow_center + tangent_dir * arrow_length / 2
                
                arrow = Arrow(
                    start=arrow_start, end=arrow_end, buff=0, color=YELLOW, stroke_width=5,
                    max_tip_length_to_length_ratio=0.4
                )
                e_arrows.add(arrow)
            
            e_label = MathTex(r"\vec{E}", font_size=42, color=YELLOW).next_to(Circle(radius=radius), RIGHT, buff=0.2)
            
            # FIX [2], [3]: Animate B-field change and dynamic E-field creation together.
            self.play(
                b_field_visual.animate.scale(1.8).set_stroke(width=12),
                AnimationGroup(*[GrowArrow(arrow) for arrow in e_arrows], lag_ratio=0.1),
                FadeIn(e_label),
                run_time=tracker.duration
            )

        with self.voiceover(text="If the magnetic field gets weaker, the electric field swirl just reverses direction.") as tracker:
            # FIX [1]: Animate B-field decreasing and smoothly rotate E-field arrows.
            self.play(
                b_field_visual.animate.scale(1/1.8).set_stroke(width=8),
                AnimationGroup(*[Rotate(arrow, angle=PI, about_point=arrow.get_center()) for arrow in e_arrows]),
                run_time=tracker.duration
            )
