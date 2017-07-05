# Working with multiple figure windows and subplots
import matplotlib.pyplot as plt
import numpy as np

t = np.arange(0.0, 2.0, 0.01)
s1 = np.sin(2*np.pi*t)
s2 = np.sin(4*np.pi*t)

for x in range(5):
    plt.figure(1)
    plt.subplot(4, 5, x + 1)
    plt.plot(t, s1)

plt.show()
