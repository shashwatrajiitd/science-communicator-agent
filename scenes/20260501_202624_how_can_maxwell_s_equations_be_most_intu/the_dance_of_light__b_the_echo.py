from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheDanceOfLightBTheEcho(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # --- Initial state from previous scene ---
        title = Text("Rule 4: The Ampere-Maxwell Law", font_size=36).to_edge(UP, buff=0.3)
        
        e_field_arrow = Arrow(
            ORIGIN, UP * 3, color=YELLOW, buff=0, 
            stroke_width=8, max_tip_length_to_length_ratio=0.2
        )
        e_label = MathTex(r"\vec{E}", font_size=42, color=YELLOW).next_to(e_field_arrow, RIGHT, buff=0.2)
        e_field_group = VGroup(e_field_arrow, e_label)

        b_radius = 1.0
        num_arrows = 8
        b_arrows = VGroup()
        for i in range(num_arrows):
            angle = i * TAU / num_arrows + PI/8
            pos = np.array([b_radius * np.cos(angle), b_radius * np.sin(angle), 0])
            tangent_dir = np.array([-np.sin(angle), np.cos(angle), 0])
            arrow = Arrow(
                pos - tangent_dir * 0.25, pos + tangent_dir * 0.25,
                buff=0, color=TEAL, stroke_width=5, max_tip_length_to_length_ratio=0.5
            )
            b_arrows.add(arrow)
        
        b_label = MathTex(r"\vec{B}", font_size=42, color=TEAL).next_to(Circle(radius=b_radius), RIGHT, buff=0.2)
        b_field_loop = VGroup(b_arrows, b_label)
        
        self.add(title, e_field_group, b_field_loop)

        # --- Beat 1 ---
        with self.voiceover(text="...but this new electric field is itself changing! And a changing electric field creates a curling magnetic field.") as tracker:
            new_b_radius = 2.0
            new_b_arrows = VGroup()
            for i in range(num_arrows):
                angle = i * TAU / num_arrows + PI/8
                pos = np.array([new_b_radius * np.cos(angle), new_b_radius * np.sin(angle), 0])
                tangent_dir = np.array([-np.sin(angle), np.cos(angle), 0])
                arrow = Arrow(
                    pos - tangent_dir * 0.35, pos + tangent_dir * 0.35,
                    buff=0, color=TEAL, stroke_width=5, max_tip_length_to_length_ratio=0.5
                )
                new_b_arrows.add(arrow)
            
            new_b_label = MathTex(r"\vec{B}", font_size=42, color=TEAL).next_to(Circle(radius=new_b_radius), RIGHT, buff=0.2)
            new_b_field_loop = VGroup(new_b_arrows, new_b_label)

            time = ValueTracker(0)
            
            def e_arrow_updater(mob):
                # Oscillate length. 2*PI gives one full cycle per second.
                new_length = 2.5 + 0.5 * np.sin(time.get_value() * 2 * PI) 
                mob.put_start_and_end_on(ORIGIN, UP * new_length)

            e_field_arrow.add_updater(e_arrow_updater)
            e_label.add_updater(lambda m: m.next_to(e_field_arrow, RIGHT, buff=0.2))

            delay = 2.5
            
            # Animate the E-field changing for the first 2.5 seconds
            self.play(
                time.animate(rate_func=linear).set_value(delay),
                run_time=delay
            )

            # Then, while the E-field continues to change, fade in the new B-field
            self.play(
                FadeIn(new_b_field_loop),
                time.animate(rate_func=linear).set_value(tracker.duration),
                run_time=max(0.1, tracker.duration - delay)
            )
            
            e_field_arrow.clear_updaters()
            e_label.clear_updaters()