from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class RuleFourTheOtherShoeDrops(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # --- Initial state from previous scene ---
        title = Text("Rule 3: Faraday's Law", font_size=36).to_edge(UP, buff=0.3)
        b_cross = Cross(stroke_color=TEAL, stroke_width=8).scale(0.5)
        b_label_initial = MathTex(r"\vec{B}", font_size=42, color=TEAL).next_to(b_cross, DR, buff=0.2)
        b_field_initial = VGroup(b_cross, b_label_initial)

        radius = 1.2
        e_arrows_initial = VGroup()
        num_arrows = 8
        arrow_length = 0.5
        for i in range(num_arrows):
            angle = i * TAU / num_arrows
            pos = np.array([radius * np.cos(angle), radius * np.sin(angle), 0])
            # Clockwise direction for decreasing B field
            tangent_dir = np.array([np.sin(angle), -np.cos(angle), 0])
            arrow = Arrow(
                pos - tangent_dir * arrow_length / 2,
                pos + tangent_dir * arrow_length / 2,
                buff=0, color=YELLOW, stroke_width=5, max_tip_length_to_length_ratio=0.4
            )
            e_arrows_initial.add(arrow)
        
        e_label_initial = MathTex(r"\vec{E}", font_size=42, color=YELLOW).next_to(Circle(radius=radius), RIGHT, buff=0.2)
        
        initial_visuals = VGroup(b_field_initial, e_arrows_initial, e_label_initial)
        self.add(title, initial_visuals)

        # --- Beat 1 ---
        with self.voiceover(text="Rule four is the perfect mirror image. A magnetic field can be created in two ways. First, by an electric current—which is just moving charges.") as tracker:
            new_title = Text("Rule 4: The Ampere-Maxwell Law", font_size=36).to_edge(UP, buff=0.3)
            
            self.play(
                Transform(title, new_title),
                FadeOut(initial_visuals),
                run_time=1.5
            )

            wire = Line(UP * 3.5, DOWN * 3.5, color=GREY, stroke_width=8)
            self.play(Create(wire), run_time=1.0)

            def create_electron():
                return VGroup(
                    Sphere(radius=0.15, color=BLUE, fill_opacity=1, resolution=(16, 16)),
                    MathTex("-", color=WHITE).scale(0.8)
                )

            electrons = VGroup(*[create_electron().move_to(wire.get_center() + UP * (2.5 - i * 1.0)) for i in range(6)])
            
            b_radius = 1.0
            b_arrows = VGroup()
            for i in range(num_arrows):
                angle = i * TAU / num_arrows + PI/8
                pos = np.array([b_radius * np.cos(angle), b_radius * np.sin(angle), 0])
                tangent_dir = np.array([-np.sin(angle), np.cos(angle), 0]) # Counter-clockwise
                arrow = Arrow(
                    pos - tangent_dir * 0.25, pos + tangent_dir * 0.25,
                    buff=0, color=TEAL, stroke_width=5, max_tip_length_to_length_ratio=0.5
                )
                b_arrows.add(arrow)
            
            b_label = MathTex(r"\vec{B}", font_size=42, color=TEAL).next_to(Circle(radius=b_radius), RIGHT, buff=0.2)
            b_field_loop = VGroup(b_arrows, b_label)
            
            self.play(
                FadeIn(electrons, shift=UP*0.5),
                Create(b_field_loop),
                run_time=1.5
            )
            
            current_group = VGroup(wire, electrons)
            self.play(
                electrons.animate(rate_func=linear).shift(DOWN * 7),
                run_time=max(0.1, tracker.duration - 4.0)
            )

        # --- Beat 2 ---
        with self.voiceover(text="But here's the brilliant insight from Maxwell: a *changing* electric field also does the trick, creating a swirling magnetic field around it, just like in rule three.") as tracker:
            e_field_arrow = Arrow(ORIGIN, UP * 0.1, color=YELLOW, buff=0, stroke_width=8, max_tip_length_to_length_ratio=0.2)
            e_label = MathTex(r"\vec{E}", font_size=42, color=YELLOW).next_to(e_field_arrow, RIGHT, buff=0.2)
            e_field = VGroup(e_field_arrow, e_label)
            b_field_loop_2 = b_field_loop.copy()

            self.play(
                FadeOut(current_group, b_field_loop),
                FadeIn(e_field),
                run_time=2.0
            )

            e_label.add_updater(lambda m: m.next_to(e_field_arrow, RIGHT, buff=0.2))
            
            self.play(
                e_field_arrow.animate.put_start_and_end_on(ORIGIN, UP * 3),
                Create(b_field_loop_2),
                run_time=max(0.1, tracker.duration - 2.0)
            )
            e_label.remove_updater(e_label.updaters[0])