from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheFourRulesOfReality(ThreeDScene, VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))
        
        # Set up 3D camera
        self.set_camera_orientation(phi=70 * DEGREES, theta=-45 * DEGREES, zoom=0.9)

        # Create icons
        rule1_icon = self.create_rule1_icon()
        rule2_icon = self.create_rule2_icon()
        rule3_icon = self.create_rule3_icon()
        rule4_icon = self.create_rule4_icon()

        icons_left = VGroup(rule1_icon, rule2_icon).arrange(DOWN, buff=1.5).to_edge(LEFT, buff=0.5)
        icons_right = VGroup(rule3_icon, rule4_icon).arrange(DOWN, buff=1.5).to_edge(RIGHT, buff=0.5)

        with self.voiceover(text="So there they are. Four rules. Charges make electric fields. Magnetic fields always loop.") as tracker:
            self.play(FadeIn(icons_left, shift=RIGHT), run_time=1.5)

        with self.voiceover(text="A changing magnetic field makes a swirling electric field. And a changing electric field or a current makes a swirling magnetic field.") as tracker:
            self.play(FadeIn(icons_right, shift=LEFT), run_time=1.5)

        all_icons = VGroup(rule1_icon, rule2_icon, rule3_icon, rule4_icon)
        
        grid_target_positions = {
            rule1_icon: [-1.5, 1.2, 0],
            rule3_icon: [1.5, 1.2, 0],
            rule2_icon: [-1.5, -1.2, 0],
            rule4_icon: [1.5, -1.2, 0],
        }

        with self.voiceover(text="Together, they don't just describe the world; they create it, painting the cosmos with light.") as tracker:
            self.play(
                *[icon.animate.move_to(pos) for icon, pos in grid_target_positions.items()],
                run_time=tracker.duration * 0.3
            )
            
            axes = ThreeDAxes(
                x_range=[-4, 4, 1], y_range=[-1.5, 1.5, 1], z_range=[-1.5, 1.5, 1],
                x_length=8, y_length=3, z_length=3
            ).set_opacity(0.7)

            e_func = lambda t: axes.c2p(t, 0, np.sin(t * 1.5))
            b_func = lambda t: axes.c2p(t, np.sin(t * 1.5), 0)

            e_wave = ParametricFunction(e_func, t_range=[-4, 4], color=YELLOW).set_shade_in_3d(True)
            b_wave = ParametricFunction(b_func, t_range=[-4, 4], color=TEAL).set_shade_in_3d(True)
            arrow = Arrow3D(start=axes.c2p(-4,0,0), end=axes.c2p(4.5,0,0), color=WHITE, resolution=8)
            
            wave_group = VGroup(axes, e_wave, b_wave, arrow)
            wave_group.scale(0.8).move_to(ORIGIN)

            self.play(
                FadeOut(all_icons, scale=0.5),
                Create(wave_group),
                run_time=tracker.duration * 0.3
            )
            
            self.move_camera(
                zoom=2.5,
                frame_center=wave_group.get_center(),
                run_time=tracker.duration * 0.4
            )
        
        self.wait(0.5)

    def create_rule1_icon(self):
        charge = Dot(color=RED, radius=0.1)
        field_lines = VGroup(*[
            Arrow(charge.get_center(), charge.get_center() + 0.6 * dir, buff=0.12, stroke_width=4, max_tip_length_to_length_ratio=0.25, tip_length=0.15)
            for dir in compass_directions(8, start_vect=RIGHT)
        ])
        return VGroup(charge, field_lines).scale(0.8)

    def create_rule2_icon(self):
        loop = Arc(radius=0.4, angle=TAU*0.95, color=BLUE, stroke_width=4).add_tip(tip_length=0.15)
        loop.rotate(-PI/2)
        return VGroup(loop)

    def create_rule3_icon(self):
        label = MathTex(r"\frac{dB}{dt}", font_size=42, color=TEAL)
        arrow_circle = Arc(radius=0.5, angle=TAU * 0.9, color=YELLOW, stroke_width=4).add_tip(tip_length=0.15)
        arrow_circle.rotate(-PI/2)
        return VGroup(label, arrow_circle).scale(0.9)

    def create_rule4_icon(self):
        label = MathTex(r"\frac{dE}{dt}", font_size=42, color=YELLOW)
        arrow_circle = Arc(radius=0.5, angle=TAU * 0.9, color=TEAL, stroke_width=4).add_tip(tip_length=0.15)
        arrow_circle.rotate(-PI/2)
        return VGroup(label, arrow_circle).scale(0.9)