from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class IntroducingTheSumTriangle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))

        title = Text("A Visual Proof for Summing Integers", font_size=42).to_edge(UP, buff=0.5)
        self.add(title)

        with self.voiceover(text="What if you wanted to add up all the numbers from 1 to, say, one hundred? It's a classic problem.") as tracker:
            sum_100 = MathTex(r"1 + 2 + 3 + \dots + 100", font_size=36)
            self.play(Write(sum_100), run_time=tracker.duration)

        with self.voiceover(text="More generally, how do we find the sum of 1 plus 2 plus 3, all the way up to any number 'n'?") as tracker:
            sum_n = MathTex(r"\text{Sum} = 1 + 2 + \dots + n", font_size=36).move_to(sum_100.get_center())
            self.play(TransformMatchingTex(sum_100, sum_n), run_time=tracker.duration)

        with self.voiceover(text="Let's visualize this. We can represent the number one with a single dot, the number two with a row of two dots, and so on.") as tracker:
            n = 5
            dot_rows = VGroup(*[
                VGroup(*[Dot(color=BLUE) for _ in range(i + 1)]).arrange(RIGHT, buff=0.25)
                for i in range(n)
            ])
            triangle_dots = dot_rows.arrange(DOWN, buff=0.25, aligned_edge=LEFT).center()
            
            self.play(
                FadeOut(sum_n),
                Succession(*[Create(row) for row in triangle_dots]),
                run_time=tracker.duration
            )

        with self.voiceover(text="When we stack these rows, they form a neat triangle. The total number of dots here is the sum we're looking for.") as tracker:
            # Calculate vertices for the outline based on the dots
            p1 = triangle_dots[0][0].get_center() + UL * 0.3
            p2 = triangle_dots[-1][0].get_center() + DL * 0.3
            p3 = triangle_dots[-1][-1].get_center() + DR * 0.3
            
            outline = Polygon(p1, p2, p3, color=YELLOW, stroke_width=3)
            
            self.play(Create(outline), run_time=tracker.duration)