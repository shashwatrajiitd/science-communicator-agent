from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheDanceOfLightATheSpark(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # --- Initial state setup (modified for correctness) ---
        # Fix 1: Corrected the title to reflect Faraday's Law.
        title = Text("Rule 3: Faraday's Law of Induction", font_size=36).to_edge(UP, buff=0.3)
        
        # This part of the setup is for a smooth transition from a hypothetical previous scene
        # showing Ampere-Maxwell, then fading to the correct setup for this scene.
        # The initial visuals from the prompt are for Ampere-Maxwell. We fade them out.
        initial_e_field_arrow = Arrow(ORIGIN, UP * 3, color=YELLOW, buff=0, stroke_width=8, max_tip_length_to_length_ratio=0.2)
        initial_e_label = MathTex(r"\vec{E}", font_size=42, color=YELLOW).next_to(initial_e_field_arrow, RIGHT, buff=0.2)
        initial_e_field = VGroup(initial_e_field_arrow, initial_e_label)
        
        b_radius = 1.0
        num_arrows = 8
        initial_b_arrows = VGroup()
        for i in range(num_arrows):
            angle = i * TAU / num_arrows + PI/8
            pos = np.array([b_radius * np.cos(angle), b_radius * np.sin(angle), 0])
            tangent_dir = np.array([-np.sin(angle), np.cos(angle), 0])
            arrow = Arrow(
                pos - tangent_dir * 0.25, pos + tangent_dir * 0.25,
                buff=0, color=TEAL, stroke_width=5, max_tip_length_to_length_ratio=0.5
            )
            initial_b_arrows.add(arrow)
        
        # Start with the incorrect title from the previous scene to transform it.
        wrong_title = Text("Rule 4: The Ampere-Maxwell Law", font_size=36).to_edge(UP, buff=0.3)
        self.add(wrong_title, initial_e_field, initial_b_arrows)


        # --- Beat 1 ---
        with self.voiceover(text="So, a changing magnetic field creates a curling electric field...") as tracker:
            b_center_arrow = Arrow(ORIGIN, UP * 2.5, color=TEAL, buff=0, stroke_width=8, max_tip_length_to_length_ratio=0.2)
            b_label = MathTex(r"\vec{B}", font_size=42, color=TEAL).next_to(b_center_arrow, RIGHT, buff=0.2)

            self.play(
                FadeOut(initial_e_field, initial_b_arrows),
                Transform(wrong_title, title),
                run_time=1.5
            )
            self.play(
                Create(b_center_arrow),
                FadeIn(b_label, shift=RIGHT*0.2),
                run_time=1.0
            )

            b_label.add_updater(lambda m: m.next_to(b_center_arrow, RIGHT, buff=0.2))
            
            remaining_time = max(0.1, tracker.duration - 2.5)
            # Fix 3: Use smooth rate_func for natural oscillation.
            self.play(
                b_center_arrow.animate.put_start_and_end_on(ORIGIN, DOWN * 2.5),
                rate_func=smooth,
                run_time=remaining_time
            )

        # --- Beat 2 ---
        with self.voiceover(text="...and little loops of this new E-field are created just next to it.") as tracker:
            e_radius = 1.2
            arrow_len = 0.5
            
            e_right = Arrow(
                RIGHT * e_radius - UP * arrow_len/2, RIGHT * e_radius + UP * arrow_len/2,
                buff=0, color=YELLOW, stroke_width=5, max_tip_length_to_length_ratio=0.4
            )
            e_left = Arrow(
                LEFT * e_radius + UP * arrow_len/2, LEFT * e_radius - UP * arrow_len/2,
                buff=0, color=YELLOW, stroke_width=5, max_tip_length_to_length_ratio=0.4
            )
            e_field_curl_start = VGroup(e_left, e_right)
            
            # Fix 2: E-field strength (opacity) is proportional to dB/dt.
            # It should be max when B passes through zero and zero at the peaks.
            e_field_curl_start.set_opacity(0)
            self.add(e_field_curl_start)

            # The b_arrow starts at DOWN*2.5 and moves to UP*2.5.
            # The rate of change is highest at the midpoint of the animation.
            self.play(
                b_center_arrow.animate.put_start_and_end_on(ORIGIN, UP * 2.5),
                UpdateFromAlphaFunc(
                    e_field_curl_start,
                    lambda mob, alpha: mob.set_opacity(np.sin(alpha * PI))
                ),
                # Fix 3: Use smooth rate_func for natural oscillation.
                rate_func=smooth,
                run_time=tracker.duration
            )

        b_label.remove_updater(b_label.updaters[0])