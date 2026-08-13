#This file generates the SEM image. It must run with the .det file as input. It will output a PNG with the same name as the .det file.
#python sem_gen.py <det_file>.det

import sys
import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider

def generate_sem (det_file):
    filename_base = os.path.splitext(os.path.basename(det_file))[0]
    output_image_path = f"{filename_base}.png"
    # This is a numpy datatype that corresponds to output files
    electron_dtype = np.dtype([
        ('x',  '=f'), ('y',  '=f'), ('z',  '=f'), # Position
        ('dx', '=f'), ('dy', '=f'), ('dz', '=f'), # Direction
        ('E',  '=f'),                             # Energy
        ('px', '=i'), ('py', '=i')])              # Pixel index

    # Open the output file
    data = np.fromfile(det_file, dtype=electron_dtype)
    print("Number of electrons detected: {}".format(len(data)))
    print(f"px range: {data['px'].min()} to {data['px'].max()}")
    print(f"py range: {data['py'].min()} to {data['py'].max()}")
    print(f"Unique py values: {np.unique(data['py']).shape[0]}")  # should be 768


    # Determine dynamic grid limits based on your actual data content
    xmin, xmax = int(data['px'].min()), int(data['px'].max())
    ymin, ymax = int(data['py'].min()), int(data['py'].max())

    # Automatically calculate the required total pixel counts for bins
    num_xbins = max(1024, xmax - xmin + 1)
    num_ybins = max(768, ymax - ymin + 1)

    # Generate uniform linear edge distributions dynamically
    xbins = np.linspace(-0.5, num_xbins - 0.5, num_xbins + 1)
    ybins = np.linspace(-0.5, num_ybins - 0.5, num_ybins + 1)

    H, xedges, yedges = np.histogram2d(data['px'], data['py'], bins=[xbins, ybins])

    print(f"\nDynamic Matrix Layout Calculated: {H.shape[0]}x{H.shape[1]} pixels")
    print(f"H min:    {H.min():.1f}")
    print(f"H max:    {H.max():.1f}")  
    print(f"H mean:   {H.mean():.2f}")
    print(f"Zero pixels: {(H==0).sum()}")

    # Separate substrate vs feature counts
    if H[H>0].size > 0:
        print(f"p10 (substrate level): {np.percentile(H[H>0], 10):.1f}")
        print(f"p50 (median):          {np.percentile(H[H>0], 50):.1f}")
        print(f"p90 (feature level):   {np.percentile(H[H>0], 90):.1f}")


    # 1. THE GAIN (Gamma Correction)
    gamma = 0.6 #initial gamma
    offset_factor = 0.4 #initial brightness
    H_adjusted = np.power(H, gamma)

    active_pixels = H_adjusted[H_adjusted > 0]

    if active_pixels.size > 0:
        # Find the actual boundaries of the electron counts
        data_min = np.percentile(active_pixels, 1) 
        data_max = np.percentile(active_pixels, 98) 
        
        #THE OFFSET (Brightness Knob)
        vmin_val = data_min - (data_max - data_min) * offset_factor
        vmax_val = data_max 
    else:
        vmin_val, vmax_val = 0, 100

    fig, ax = plt.subplots(figsize=(10.24, 7.68))
    fig.subplots_adjust(bottom=0.25)

    #RENDER THE IMAGE
    im = ax.imshow(
        H_adjusted.T, 
        cmap='gray', 
        vmin=vmin_val, 
        vmax=vmax_val, 
        origin='upper', 
        aspect='equal'
    )

    plt.colorbar(im, ax=ax, label='Electron Counts')
    # plt.xlabel('x pixel')
    # plt.ylabel('y pixel')

    axgamma = fig.add_axes((0.25, 0.12, 0.65, 0.03))
    gamma_slider = Slider(
        ax=axgamma, 
        label='Contrast (Gain/Gamma)', 
        valmin=0.0, 
        valmax=2.0, 
        valinit=gamma
    )

    axoffset = fig.add_axes((0.25, 0.07, 0.65, 0.03))
    offset_slider = Slider(
        ax=axoffset, 
        label='Brightness (Offset)', 
        valmin=0.0, 
        valmax=1.0, 
        valinit=offset_factor
    )

    def update(val):
        gamma = gamma_slider.val
        offset_factor = offset_slider.val
        
        H_adjusted = np.power(H, gamma)
        
        active_pixels = H_adjusted[H_adjusted > 0]
        if active_pixels.size > 0:
            data_min = np.percentile(active_pixels, 1) 
            data_max = np.percentile(active_pixels, 98) 
            vmin_val = data_min - (data_max - data_min) * offset_factor
            vmax_val = data_max 
        else:
            vmin_val, vmax_val = 0, 100

        im.set_data(H_adjusted.T)
        im.set_clim(vmin=vmin_val, vmax=vmax_val)
        fig.canvas.draw_idle()

    gamma_slider.on_changed(update)
    offset_slider.on_changed(update)

    resetax = plt.axes([0.8, 0.025, 0.1, 0.04])
    button = Button(resetax, 'Reset', hovercolor='0.975')

    not_saveax = plt.axes([0.021 , 0.024, 0.1, 0.04])
    not_save = Button(not_saveax, 'Do not save\nto PNG', color = "red", hovercolor = "pink")

    # save_btax = plt.axes([0.8, 0.8, 0.1, 0.4])
    # save_bt = Button(save_btax, 'View and Save', color = "green", hovercolor = "limegreen")

    ax.set_title(f"Image will be saved as {output_image_path}")
    save_flag = True

    def reset(event):
        gamma_slider.reset()
        offset_slider.reset()
    button.on_clicked(reset)

    def no_save(event):
        nonlocal save_flag, not_save, output_image_path
        save_flag = not save_flag
        if not save_flag:
            not_save.color = "dodgerblue"
            not_save.hovercolor = "lightblue"
            not_save.label.set_text("Save to PNG")
            ax.set_title(f"Image will not be saved")
            # save_bt.color = "orangered"
            # save_bt.hovercolor = "lightsalmon"
            # save_bt.label.set_text("Cancel") 
        else:
            not_save.color = "red"
            not_save.hovercolor = "pink"
            not_save.label.set_text("Do not save\nto PNG")
            ax.set_title(f"Image will be saved as {output_image_path}")
            # save_bt.color = "orangered"
            # save_bt.hovercolor = "lightsalmon"
            # save_bt.label.set_text("Cancel") 
        fig.canvas.draw_idle()

    not_save.on_clicked(no_save)

    plt.show()
    if save_flag:
        matplotlib.pyplot.imsave(output_image_path,H_adjusted.T, 
        cmap='gray', 
        vmin=vmin_val, 
        vmax=vmax_val,  
        )
        print(f"1024x768 aspect image file saved to workspace: {os.path.basename(output_image_path)}")
    else:
        print("Image was not saved")


if __name__ == "__main__":
    # Find out which file to open
    if len(sys.argv) < 2:
        print("No output file provided")
        sys.exit()
    filename = sys.argv[1]
    if not os.path.exists(filename):
        print("File {} cannot be found".format(filename))
        sys.exit()
    
    # Call the main function to process the file
    generate_sem(det_file=filename)