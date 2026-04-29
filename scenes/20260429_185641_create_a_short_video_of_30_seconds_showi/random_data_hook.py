from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np

# Helper function to create diverse mobjects representing data points.
# This is defined outside the class for clarity, but could also be a static method.
def create_random_mobject():
    """Creates one of three types of mobjects: a person icon, a number, or a bean shape."""
    rand_choice = np.random.choice(["person", "number", "bean"])
    
    if rand_choice == "person":  # Represents 'height of people'
        head = Circle(radius=0.12, color=BLUE, fill_opacity=1).move_to(UP * 0.12)
        body = Rectangle(height=0.24, width=0.18, color=BLUE, fill_opacity=1).next_to(head, DOWN, buff=0)
        mob = VGroup(head, body)
    elif rand_choice == "number":  # Represents 'results of an exam'
        mob = Text(str(np.random.randint(65, 100)), color=BLUE, font_size=36)
    else:  # Represents 'size of coffee beans'
        mob = Ellipse(width=0.25, height=0.15, color=BLUE, fill_opacity=1)
    
    # Scale all mobjects to a similar small size for visual consistency.
    mob.scale(0.5)
    return mob

class RandomDataHook(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Puck"))

        # --- Beat 1: Show a cloud of random data points ---
        with self.voiceover(text="Ever wonder what connects the height of people, the results of an exam, or even the size of coffee beans?") as tracker:
            num_points = 120
            
            # Create a VGroup to hold all the floating data points.
            data_cloud = VGroup()
            for _ in range(num_points):
                mob = create_random_mobject()
                # Position points randomly within the portrait frame's bounds.
                # Frame width is ~4.5, height is 8.0.
                mob.move_to([
                    np.random.uniform(-2.0, 2.0),
                    np.random.uniform(0.5, 3.5),
                    0
                ])
                data_cloud.add(mob)

            self.play(
                LaggedStart(
                    *[FadeIn(p, shift=UP * 0.5) for p in data_cloud],
                    lag_ratio=0.04
                ),
                run_time=tracker.duration
            )

        # --- Beat 2: Points fall and stack into a histogram ---
        with self.voiceover(text="They might seem random, but when you gather enough of them, a stunning pattern emerges.") as tracker:
            num_bins = 11
            x_min, x_max = -2.0, 2.0
            bins = np.linspace(x_min, x_max, num_bins + 1)
            
            # Generate target data from a normal distribution to determine the histogram shape.
            target_data = np.random.normal(loc=0, scale=0.6, size=num_points)
            # Assign each data point to a bin index.
            binned_indices = np.digitize(target_data, bins) - 1
            
            animations = []
            
            # Pre-sort mobjects into lists corresponding to their destination bin.
            points_in_bins = [[] for _ in range(num_bins)]
            for i, p in enumerate(data_cloud):
                bin_index = binned_indices[i]
                if 0 <= bin_index < num_bins:
                    points_in_bins[bin_index].append(p)
            
            # Calculate final positions for each mobject to form stacked bars.
            y_base = -3.8  # Bottom of the screen in portrait mode.
            for bin_index, points in enumerate(points_in_bins):
                target_x = (bins[bin_index] + bins[bin_index + 1]) / 2
                current_y_top = y_base
                
                for p in points:
                    # Position the object's center so its bottom rests on the current top of the stack.
                    target_y = current_y_top + p.height / 2
                    target_pos = [target_x, target_y, 0]
                    animations.append(p.animate.move_to(target_pos))
                    
                    # Update the top of the stack for the next object in this bin.
                    current_y_top += p.height

            self.play(
                LaggedStart(*animations, lag_ratio=0.01),
                run_time=tracker.duration
            )
            
            # The final arrangement of points represents the 'data_histogram' shared object.
            # It is composed of blue icons and has an irregular but centered shape.