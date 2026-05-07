from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheDanceOfLightCPropagation(ThreeDScene, VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # --- Initial state from previous scene ---
        title = Text("Rule 4: The Ampere-Maxwell Law", font_size=36).to_edge(UP, buff=0.3)
        self.add_fixed_in_frame_mobjects(title)

        e_field_arrow = Arrow(ORIGIN, UP * 2, color=YELLOW, buff=0, stroke_width=8, max_tip_length_to_length_ratio=0.25)
        e_label = MathTex(r"\vec{E}", font_size=42, color=YELLOW).next_to(e_field_arrow, RIGHT, buff=0.2)
        e_field = VGroup(e_field_arrow, e_label)

        b_radius = 1.0
        num_b_arrows = 10
        b_arrows = VGroup()
        for i in range(num_b_arrows):
            angle = i * TAU / num_b_arrows
            pos = np.array([b_radius * np.cos(angle), b_radius * np.sin(angle), 0])
            tangent_dir = np.array([-np.sin(angle), np.cos(angle), 0])
            arrow = Arrow(
                pos - tangent_dir * 0.2, pos + tangent_dir * 0.2,
                buff=0, color=TEAL, stroke_width=5, max_tip_length_to_length_ratio=0.5
            )
            b_arrows.add(arrow)
        
        initial_group = VGroup(e_field, b_arrows)
        self.add(initial_group)
        
        # --- Beat 1 ---
        with self.voiceover(text="This cycle of a changing B creating a changing E, creating a changing B, leaps across space.") as tracker:
            self.play(FadeOut(title), run_time=1.0)
            
            axes = ThreeDAxes(
                x_range=[0, 8, 2], y_range=[-1.5, 1.5, 1], z_range=[-1.5, 1.5, 1],
                x_length=4.0, y_length=3, z_length=3,
            ).move_to(ORIGIN)
            
            self.move_camera(phi=75 * DEGREES, theta=-70 * DEGREES, zoom=0.9)
            
            # Transition from 2D representation to 3D wave
            self.play(FadeOut(initial_group), Create(axes), run_time=1.5)

            time = ValueTracker(0)
            
            # Use always_redraw to create a continuously propagating wave
            e_wave = always_redraw(
                lambda: axes.plot(lambda x: np.cos(x - time.get_value()), x_range=[0, 8], color=YELLOW)
            )
            b_wave = always_redraw(
                lambda: axes.plot(lambda x: np.cos(x - time.get_value()), x_range=[0, 8], color=TEAL).apply_function(
                    lambda p: [p[0], 0, p[1]]
                )
            )
            
            self.add(e_wave, b_wave)
            # Animate the wave propagation for the remainder of the beat
            self.play(
                time.animate.set_value(1.5 * PI),
                rate_func=linear,
                run_time=max(0.1, tracker.duration - 2.5) # Subtract time for setup animations
            )

        # --- Beat 2 ---
        with self.voiceover(text="This self-sustaining wave is an electromagnetic wave. It's light.") as tracker:
            propagation_arrow = Arrow(axes.c2p(0,0,0), axes.c2p(8,0,0), buff=0, color=WHITE, stroke_width=5)
            
            propagation_label = Text("Direction of Light", font_size=32, color=WHITE)
            propagation_label.set_shade_in_3d(True)
            propagation_label.next_to(propagation_arrow.get_end(), UR, buff=0.2)
            propagation_label.rotate(75 * DEGREES, axis=RIGHT)

            # Combine propagation animation with arrow/label creation to avoid pauses
            self.play(
                Create(propagation_arrow),
                Write(propagation_label),
                time.animate.set_value(3 * PI), # Continue the wave motion
                rate_func=linear,
                run_time=tracker.duration
            )
        
        # Cleanup updaters
        e_wave.clear_updaters()
        b_wave.clear_updaters()