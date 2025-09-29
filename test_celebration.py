import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def celebrate_animation():
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_facecolor('black')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # generate some random points for confetti
    n = 500
    x = np.random.rand(n)
    y = np.random.rand(n)
    colors = np.random.rand(n, 3)
    sizes = np.random.randint(20, 80, n)

    scat = ax.scatter(x, y, s=sizes, c=colors)

    def update(frame):
        # update positions randomly
        scat.set_offsets(np.c_[np.random.rand(n), np.random.rand(n)])
        return scat,

    ani = FuncAnimation(fig, update, frames=30, interval=150, blit=True, repeat=False)
    plt.show()  # blocks until closed

# Example usage inside your loop:

celebrate_animation()
