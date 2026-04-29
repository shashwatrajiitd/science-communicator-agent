from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

class WhyItHappens(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Puck"))

        # Configure for 9:16 portrait aspect ratio
        self.camera.frame_width = 4.5
        self.camera.frame_height = 8.0

        # Helper function to create a die visual
        def create_die(value):
            square = Square(side_length=0.7, stroke_color=WHITE, fill_color=BLACK, fill_opacity=1)
            num = Integer(value, color=WHITE).scale(0.7)
            num.move_to(square.get_center())
            return VGroup(square, num)

        # --- Beat 1 ---
        with self.voiceover(text="But why does this happen? It's often because outcomes are the sum of many small, random factors.") as tracker:
            # Create and show dice
            die1 = create_die(3)
            die2 = create_die(5)
            dice_group = VGroup(die1, die2).arrange(RIGHT, buff=0.3).to_edge(UP, buff=0.5)
            
            # Create and show sum
            sum_text = MathTex(r"3 + 5 = 8", font_size=36).next_to(dice_group, DOWN, buff=0.4)
            
            self.play(
                FadeIn(dice_group, shift=DOWN),
                Write(sum_text),
                run_time=tracker.duration * 0.6
            )

            # Create the initial histogram with one data point
            # Sums of two dice range from 2 to 12 (11 possible values)
            # The sum 8 is at index 6 (since 2 is index 0)
            initial_counts = [0] * 11
            initial_counts[8 - 2] = 10 # Use a value > 1 for visibility
            
            chart = BarChart(
                values=initial_counts,
                bar_names=[str(i) for i in range(2, 13)],
                y_range=[0, 100, 20],
                x_length=4.0,
                y_length=2.5,
                bar_colors=[BLUE],
            ).next_to(sum_text, DOWN, buff=0.5)
            chart.x_axis.labels.set_font_size(24)

            self.play(Create(chart), run_time=tracker.duration * 0.4)

        # --- Beat 2 ---
        with self.voiceover(text="Take dice rolls. The sum of two dice is most likely to be seven, with other sums becoming rarer. This is the Central Limit Theorem in action.") as tracker:
            # Simulate many rolls to get the final distribution
            num_rolls = 500
            rolls1 = np.random.randint(1, 7, num_rolls)
            rolls2 = np.random.randint(1, 7, num_rolls)
            sums = rolls1 + rolls2
            final_counts = [np.count_nonzero(sums == i) for i in range(2, 13)]
            
            # Create the final chart for the transformation
            max_y = max(final_counts) * 1.1
            y_step = round(max_y / 5) if max_y > 5 else 1
            final_chart = BarChart(
                values=final_counts,
                bar_names=[str(i) for i in range(2, 13)],
                y_range=[0, max_y, y_step],
                x_length=4.0,
                y_length=2.5,
                bar_colors=[BLUE],
            ).move_to(chart)
            final_chart.x_axis.labels.set_font_size(24)

            clt_title = Text("Central Limit Theorem", font_size=36).to_edge(DOWN, buff=0.5)

            # Get the number mobjects from the dice to update them
            die1_num, die2_num = dice_group[0][1], dice_group[1][1]

            def update_dice_numbers(mob):
                d1_val = np.random.randint(1, 7)
                d2_val = np.random.randint(1, 7)
                die1_num.set_value(d1_val)
                die2_num.set_value(d2_val)

            dice_group.add_updater(update_dice_numbers)
            
            self.play(
                Transform(chart, final_chart),
                FadeOut(sum_text), # Clean up sum text from beat 1
                Write(clt_title),
                run_time=tracker.duration
            )
            
            dice_group.remove_updater(update_dice_numbers)
            # Set a final state for the dice for a clean end frame
            die1_num.set_value(3)
            die2_num.set_value(4)