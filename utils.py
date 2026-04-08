import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
import matplotlib.lines as mlines
from matplotlib.collections import PathCollection

def parse_filename(filename):
    filename = filename.split('.')[0]
    material, measurement_type, device_number, condition = filename.split('_')
    return {"material": material, "measurement_type": measurement_type,
             "device_number": device_number, "condition": condition}

def group_files(measurement_type, csv_files):
    measurement_type_list = [f for f in csv_files if parse_filename(f)["measurement_type"] == measurement_type]
    return measurement_type_list

def determine_folder_name(folder, is_bad):
    if is_bad:
        return folder / Path('bad')
    else:
        return folder
def plot_settings():
    plt.tick_params(axis='y', which="both", direction='in')
    plt.tick_params(axis='x', direction='in')
    plt.grid(True, which='major', linestyle='--', linewidth=0.5, alpha=0.7) # major, minor or both
    # plt.tight_layout()


def wavelength_to_color(wl):
    norm = plt.Normalize(450, 680)
    cmap = plt.cm.turbo
    return cmap(norm(wl))

import math


# physics-based wavelength to RGB function
def wavelength_to_rgb_physics(wl, gamma=0.8):
    if wl < 380 or wl > 780:
        return (0, 0, 0)

    if 380 <= wl < 440:
        r = -(wl - 440) / (440 - 380)
        g = 0.0
        b = 1.0
    elif 440 <= wl < 490:
        r = 0.0
        g = (wl - 440) / (490 - 440)
        b = 1.0
    elif 490 <= wl < 510:
        r = 0.0
        g = 1.0
        b = -(wl - 510) / (510 - 490)
    elif 510 <= wl < 580:
        r = (wl - 510) / (580 - 510)
        g = 1.0
        b = 0.0
    elif 580 <= wl < 645:
        r = 1.0
        g = -(wl - 645) / (645 - 580)
        b = 0.0
    else:
        r = 1.0
        g = 0.0
        b = 0.0

    if 380 <= wl < 420:
        factor = 0.3 + 0.7*(wl - 380) / (420 - 380)
    elif 645 <= wl < 780:
        factor = 0.3 + 0.7*(780 - wl) / (780 - 645)
    else:
        factor = 1.0

    r = (factor * r) ** gamma
    g = (factor * g) ** gamma
    b = (factor * b) ** gamma

    return (r, g, b)




def vertical_legend(ax, plot_width=2, fontsize=15, dpi=300, save_path=None):
    """
    Save a vertically stacked legend as a separate figure with tight layout.
    Handles both Line2D (plt.plot) and scatter (PathCollection) objects.

    Parameters:
        ax (matplotlib.axes.Axes): Axis containing plotted elements.
        filename (str): Path to save the legend.
        plot_width (float): Width of the figure in inches.
        fontsize (int): Font size for legend text.
        dpi (int): Resolution of the saved figure.
    """
    # Create proxies for scatter objects
    handles, labels = ax.get_legend_handles_labels()
    proxies = []
    for h in handles:
        if isinstance(h, PathCollection):
            # use first color in the PathCollection for the marker
            facecolor = h.get_facecolor()[0] if len(h.get_facecolor()) > 0 else 'k'
            edgecolor = h.get_edgecolor()[0] if len(h.get_edgecolor()) > 0 else 'k'
            marker = 'o'  # default marker
            proxy = mlines.Line2D([], [], color=edgecolor, marker=marker,
                                  linestyle='None', markersize=6)
            proxies.append(proxy)
        else:
            proxies.append(h)

    # Create figure with placeholder height
    fig = plt.figure(figsize=(plot_width, 2))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis('off')

    # Create vertical legend
    leg = ax.legend(
        proxies, labels,
        loc='center',
        ncol=1,
        frameon=False,
        fontsize=fontsize,
        handlelength=1.5,
        handleheight=1,
        labelspacing=0.5,
        borderaxespad=0
    )

    # Draw to get legend bbox
    fig.canvas.draw()
    bbox = leg.get_window_extent()
    legend_height_inch = bbox.height / dpi

    # Resize figure to fit legend tightly
    if save_path:
        fig.set_size_inches(plot_width, legend_height_inch + 0.05)  # small padding
        fig.savefig(save_path, dpi=dpi, bbox_inches='tight', pad_inches=0)
        plt.close(fig)


def load_signal(file_path):
    """
    Load CSV and return (df, t, y) where:
      - df: full DataFrame
      - t: first column
      - y: second column
    """
    df = pd.read_csv(file_path).dropna(how='all')
    t = df.iloc[:, 0]
    y = df.iloc[:, 1]
    return df, t, y

def rise_time(x, y):
    """
    Compute rise time (10% → 90%) for a rising segment.
    
    Parameters:
        x : np.ndarray
            Time array (interpolated)
        y : np.ndarray
            Signal array (interpolated)
    
    Returns:
        float : rise time in the same units as x
    """
    y_min = y[0]  # first point
    y_max = y[-1] # last point
    
    y_10 = y_min + 0.1 * (y_max - y_min)
    y_90 = y_min + 0.9 * (y_max - y_min)
    
    # Interpolate to find exact times
    f_inv = interp1d(y, x, kind='linear', fill_value='extrapolate')
    t_10 = f_inv(y_10)
    t_90 = f_inv(y_90)
    actual_light_time = x[-1] - x[0]
    return float(t_90 - t_10), actual_light_time

def decay_time(x, y):
    """
    Compute decay time (90% → 10%) for a falling segment.
    
    Parameters:
        x : np.ndarray
            Time array (interpolated)
        y : np.ndarray
            Signal array (interpolated)
    
    Returns:
        float : decay time in the same units as x
    """
    y_max = y[0]  # first point
    y_min = y[-1] # last point
    
    y_90 = y_min + 0.9 * (y_max - y_min)
    y_10 = y_min + 0.1 * (y_max - y_min)
    
    # Interpolate to find exact times
    f_inv = interp1d(y, x, kind='linear', fill_value='extrapolate')
    t_90 = f_inv(y_90)
    t_10 = f_inv(y_10)
    actual_dark_time = x[-1] - x[0]    
    return float(t_10 - t_90), actual_dark_time

def plot_time(time_file, process_folder, image_folder=None):
    time_file_path = process_folder / time_file
    
    parsed_info = parse_filename(time_file)

    device_number = parsed_info["device_number"]
    measurement_type = parsed_info["measurement_type"]
    material = parsed_info["material"]

    time_df = pd.read_csv(time_file_path)
    
    x_label, y_label = time_df.columns
    plt.plot(time_df[x_label], np.abs(time_df[y_label]), color='red')
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(f'device number: {device_number}')
    # plt.legend()
    # plt.yscale('log')

    plot_settings()
    if image_folder:
        plt.savefig(image_folder / f'{material}_{measurement_type}_{device_number}.png', dpi=300)
        plt.close()
    else:
        plt.show()


def plot_idvg_dark_light(dark_file, light_file, process_folder, image_folder=None):
    dark_file_path = process_folder / dark_file
    light_file_path = process_folder/ light_file

    parsed_info = parse_filename(dark_file)
    device_number = parsed_info["device_number"]
    measurement_type = parsed_info["measurement_type"]
    material = parsed_info["material"]

    dark_df = pd.read_csv(dark_file_path)
    light_df = pd.read_csv(light_file_path)
    x_label, y_label = dark_df.columns
    
    plt.plot(dark_df[x_label], np.abs(dark_df[y_label]), color='black', label='dark')
    plt.plot(light_df[x_label], np.abs(light_df[y_label]), color='red', label='light')
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(f'device number: {device_number}')
    plt.legend()
    plt.yscale('log')

    plot_settings()
    if image_folder:
        plt.savefig(image_folder / f'{material}_{measurement_type}_{device_number}.png', dpi=300)
        plt.close()
    else:
        plt.show()

def plot_idvg_dark(dark_file, process_folder, image_folder=None):
    dark_file_path = process_folder / dark_file

    parsed_info = parse_filename(dark_file)
    device_number = parsed_info["device_number"]
    measurement_type = parsed_info["measurement_type"]
    material = parsed_info["material"]

    dark_df = pd.read_csv(dark_file_path)
    x_label, y_label = dark_df.columns
    
    plt.plot(dark_df[x_label], np.abs(dark_df[y_label]), color='black', label='dark')
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(f'device number: {device_number}')
    plt.legend()
    plt.yscale('log')

    plot_settings()
    if image_folder:
        plt.savefig(image_folder / f'{material}_{measurement_type}_{device_number}.png', dpi=300)
        plt.close()
    else:
        plt.show()

def plot_idvg_dark_multi(dark_file, process_folder):
    dark_file_path = process_folder / dark_file

    parsed_info = parse_filename(dark_file)
    device_number = parsed_info["device_number"]
    measurement_type = parsed_info["measurement_type"]
    material = parsed_info["material"]

    dark_df = pd.read_csv(dark_file_path)
    x_label, y_label = dark_df.columns
    
    plt.plot(dark_df[x_label], np.abs(dark_df[y_label]), label=f'{device_number}')
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    # plt.title(f'device number: {device_number}')
    plt.yscale('log')

    plot_settings()

    