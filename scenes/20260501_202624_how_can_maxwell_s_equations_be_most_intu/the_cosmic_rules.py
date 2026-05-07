from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class TheCosmicRules(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        # --- Section 1: Maxwell's Equations ---
        title = Tex("Maxwell's Equations", font_size=42).to_edge(UP, buff=0.5)
        
        eqs_tex = [
            r"\oint \vec{E} \cdot d\vec{A} = \frac{Q_{enc}}{\epsilon_0}",
            r"\oint \vec{B} \cdot d\vec{A} = 0",
            r"\oint \vec{E} \cdot d\vec{l} = -\frac{d\Phi_B}{dt}",
            r"\oint \vec{B} \cdot d\vec{l} = \mu_0 I_{enc} + \mu_0 \epsilon_0 \frac{d\Phi_E}{dt}"
        ]
        
        # Break the long 4th equation into two lines for better readability
        eqs_tex[3] = r"\oint \vec{B} \cdot d\vec{l} = \mu_0 I_{enc} \\ + \mu_0 \epsilon_0 \frac{d\Phi_E}{dt}"

        equations_mobs = VGroup(*[MathTex(tex, font_size=32) for tex in eqs_tex])
        equations_mobs.arrange(DOWN, buff=0.6).move_to(ORIGIN)

        beat1_text = "The universe runs on a handful of simple rules. For everything electric and magnetic, from the spark in your neurons to the light from distant stars, the rules are these four equations."
        with self.voiceover(text=beat1_text) as tracker:
            animation_time = 4.0
            self.play(
                LaggedStart(
                    Write(title),
                    *[Write(eq) for eq in equations_mobs],
                    lag_ratio=0.2,
                ),
                run_time=animation_time
            )
            if tracker.duration > animation_time:
                self.wait(tracker.duration - animation_time)

        # --- Section 2: The Four Rules (Icons) ---
        
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

        beat2_text = "But we don't need to get lost in the math. We can think of them as four simple 'rules of the road' for electric and magnetic fields."
        with self.voiceover(text=beat2_text) as tracker:
            animation_time = 2.0
            self.play(
                FadeOut(VGroup(title, equations_mobs), shift=UP*0.5),
                FadeIn(icons, shift=DOWN*0.5),
                run_time=animation_time
            )
            if tracker.duration > animation_time:
                self.wait(tracker.duration - animation_time)
