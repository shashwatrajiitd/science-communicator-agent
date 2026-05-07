from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class RuleOneChargesRadiate(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Create icons from the previous scene to ensure a continuous cut.
        # Icon 1: Gauss's Law for E (Source)
        icon1 = VGroup(
            Dot(color=YELLOW, radius=0.08),
            Tex("+", color=YELLOW, font_size=48).move_to(ORIGIN),
            *[Arrow(ORIGIN, direction * 0.6, buff=0.15, stroke_width=4, max_tip_length_to_length_ratio=0.2) for direction in compass_directions(8, start_vect=RIGHT)]
        )

        # Icon 2: Gauss's Law for B (Loops)
        icon2 = Arc(radius=0.4, start_angle=PI/2, angle=-TAU*0.9, color=BLUE, stroke_width=5).add_tip(tip_length=0.2)

        # Icon 3: Faraday's Law (Changing B -> E)
        icon3 = VGroup(
            Tex(r"$\Delta B$", color=GREEN, font_size=42),
            Arc(radius=0.6, start_angle=PI/2, angle=-TAU*0.9, color=ORANGE, stroke_width=5).add_tip(tip_length=0.2)
        )

        # Icon 4: Ampere-Maxwell Law (Current -> B)
        current_arrow = Arrow(DOWN*0.3, UP*0.3, buff=0, stroke_width=5, color=WHITE, max_tip_length_to_length_ratio=0.4)
        current_label = Tex("I", font_size=42).next_to(current_arrow, RIGHT, buff=0.15)
        current_group = VGroup(current_arrow, current_label)
        b_curl_4 = Arc(radius=0.6, start_angle=0, angle=TAU*0.9, color=BLUE, stroke_width=5).add_tip(tip_length=0.2)
        icon4 = VGroup(current_group, b_curl_4)

        icons = VGroup(icon1, icon2, icon3, icon4).arrange_in_grid(2, 2, buff=1.2).scale(0.9)
        icons.move_to(ORIGIN)
        
        self.add(icons)

        with self.voiceover(text="Rule one: Electric charges create electric fields. A positive charge is like a source, with the field pointing straight out in all directions.") as tracker:
            positive_charge_dot = Dot(point=ORIGIN, radius=0.2, color=RED)
            positive_charge_sign = Tex("+", font_size=48, color=WHITE).move_to(positive_charge_dot.get_center())
            positive_charge = VGroup(positive_charge_dot, positive_charge_sign)

            field_lines_out = VGroup()
            for direction in compass_directions(12, start_vect=RIGHT):
                field_lines_out.add(Arrow(ORIGIN + direction * 0.3, ORIGIN + direction * 1.5, buff=0, stroke_width=5, color=YELLOW, max_tip_length_to_length_ratio=0.15))

            animation_time = 2.0
            self.play(
                FadeOut(icons, shift=UP*0.2),
                FadeIn(positive_charge, shift=DOWN*0.2),
                Create(field_lines_out),
                run_time=animation_time
            )
            if tracker.duration > animation_time:
                self.wait(tracker.duration - animation_time)

        with self.voiceover(text="And a negative charge is like a sink, with the field lines all pointing inward.") as tracker:
            # Shared object: electron
            electron_dot = Dot(point=ORIGIN, radius=0.15, color=BLUE)
            electron_sign = Tex("-", font_size=36, color=WHITE).move_to(electron_dot.get_center())
            electron = VGroup(electron_dot, electron_sign)
            
            field_lines_in = VGroup()
            for direction in compass_directions(12, start_vect=RIGHT):
                 field_lines_in.add(Arrow(ORIGIN + direction * 1.5, ORIGIN + direction * 0.25, buff=0, stroke_width=5, color=YELLOW, max_tip_length_to_length_ratio=0.15))

            animation_time = 1.5
            self.play(
                ReplacementTransform(positive_charge, electron),
                ReplacementTransform(field_lines_out, field_lines_in),
                run_time=animation_time
            )
            if tracker.duration > animation_time:
                self.wait(tracker.duration - animation_time)
