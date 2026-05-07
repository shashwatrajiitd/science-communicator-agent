from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class RuleTwoMagnetismIsALoop(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # Recreate final state of previous scene for continuity
        electron_dot = Dot(point=ORIGIN, radius=0.15, color=BLUE)
        electron_sign = Tex("-", font_size=36, color=WHITE).move_to(electron_dot.get_center())
        electron = VGroup(electron_dot, electron_sign)
        
        field_lines_in = VGroup()
        for i in range(12):
            angle = i * TAU / 12
            direction = np.array([np.cos(angle), np.sin(angle), 0])
            field_lines_in.add(Arrow(ORIGIN + direction * 1.5, ORIGIN + direction * 0.25, buff=0, stroke_width=5, color=YELLOW, max_tip_length_to_length_ratio=0.15))

        initial_scene_group = VGroup(electron, field_lines_in)
        self.add(initial_scene_group)

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
            # This internal line is key for showing the loop is closed *through* the magnet
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

        with self.voiceover(text="Rule two is about magnetism. Magnetic fields never start or stop anywhere. They always form closed loops.") as tracker:
            magnet_and_fields = create_magnet_with_fields(ORIGIN, 3.0, 1.0)
            magnet_group = magnet_and_fields[0]
            fields_group = magnet_and_fields[1]
            
            # Fade in magnet first
            self.play(
                FadeOut(initial_scene_group, scale=0.5),
                FadeIn(magnet_group, scale=1.2),
                run_time=2.5
            )
            # Then create the field lines to match the narration
            self.play(
                Create(fields_group),
                run_time=max(0.1, tracker.duration - 2.5)
            )

        with self.voiceover(text="You can't have an isolated 'north' or 'south' pole. If you try to cut a magnet in half, you just get two smaller magnets, each with its own loops.") as tracker:
            cutting_line = DashedLine(LEFT * 2, RIGHT * 2, color=YELLOW)
            
            top_magnet_and_fields = create_magnet_with_fields(UP * 2.0, 2.0, 0.8)
            bottom_magnet_and_fields = create_magnet_with_fields(DOWN * 2.0, 2.0, 0.8)
            
            new_magnets_group = VGroup(top_magnet_and_fields[0], bottom_magnet_and_fields[0])
            new_fields_group = VGroup(top_magnet_and_fields[1], bottom_magnet_and_fields[1])

            # Wait for the narration cue "cut a magnet"
            self.wait(3.0)
            self.play(Create(cutting_line), run_time=0.5)

            # Animate the split more gracefully
            self.play(
                FadeOut(cutting_line),
                FadeOut(fields_group),
                Transform(magnet_group, new_magnets_group),
                run_time=1.5
            )
            self.play(
                Create(new_fields_group),
                run_time=max(0.1, tracker.duration - 3.0 - 0.5 - 1.5)
            )
