#This code is used to create a visualization of the user's features
#and allow the user to select the area they want to image with the appropriate magnificaton
#To do:
#implement rotation of plot by 90 deg
import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
import tqdm
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor
import matplotlib.patches as patches 
from matplotlib.widgets import TextBox, Button 
from matplotlib.collections import PolyCollection

#for image selection and magnification
#   top down view of .tri from mat
#   box of set width from user_mag
#   drag and choose x and y linspace from the pixels that match?
updating_programmatically = False
#Functions

def plottri(file_name):

    #Acquire .tri file
    tri_file = f"{file_name}.tri"
    if not os.path.exists(tri_file):
	    print(".tri File {} cannot be found".format(tri_file))
	    sys.exit()

    #Load .tri data, filter out identical pairs, and extract vertices
    raw_data = np.loadtxt(tri_file)
    non_identical_mask = raw_data[:, 0] != raw_data[:, 1]
    tri_data = raw_data[non_identical_mask]

    mat_in = tri_data[:, 0]
    mat_out = tri_data[:,1]
    v1 = tri_data[:, 2:5]  
    v2 = tri_data[:, 5:8]  
    v3 = tri_data[:, 8:11]
    nTri = tri_data.shape[0]

    #UNIQUE COLORS for materials
    unique_pairs = np.unique(np.column_stack((mat_in, mat_out)), axis=0)
    nGroups = unique_pairs.shape[0]
    cmap = plt.get_cmap('tab10', nGroups)
    color_dict = {tuple(pair): cmap(i) for i, pair in enumerate(unique_pairs)}
    FaceColors_list = [color_dict[(r_in, r_out)] for r_in, r_out in zip(mat_in, mat_out)]
    FaceColors = np.array(FaceColors_list) 
    
    #VERTICES
    X = np.array([v1[:,0], v2[:,0], v3[:,0]])
    Y = np.array([v1[:,1], v2[:,1], v3[:,1]])

    while True:
        try:
            user_mag = float(input("Enter magnification: "))
            if user_mag <= 0:
                print("Error: Magnification must be greater than zero. Try again.")
                continue
            break
        except ValueError:
            print("Error: Please enter a valid number.")

    # SEM FOV
    FOV_CONSTANT = 359000000  # My data says 359000000, but Zeiss calibration constant  is (114.3mm)  
    fov_x = FOV_CONSTANT / user_mag
    fov_y = fov_x * (768 / 1024)  # Maintains the perfect 1024x768 (4:3) aspect ratio

    print(f"\nCalculated SEM FOV for {user_mag}x magnification:")
    print(f"  Width (X span): {fov_x:.2f} units")
    print(f"  Height (Y span): {fov_y:.2f} units")

    # 2D plotting
    x_triangles = X.T
    y_triangles = Y.T

    fig, ax = plt.subplots(figsize=(10, 9))
    plt.subplots_adjust(bottom=0.32)  


    verts = [np.column_stack((x_triangles[i], y_triangles[i])) for i in tqdm.tqdm(range(len(x_triangles)), desc="Building geometry")]


    MAX_DISPLAY = 50000  # Adjust this until the window feels responsive
    if len(verts) > MAX_DISPLAY:
        idx = np.random.choice(len(verts), MAX_DISPLAY, replace=False)
        display_verts = [verts[i] for i in idx]
        display_colors = FaceColors[idx]
    else:
        display_verts = verts
        display_colors = FaceColors

    col = PolyCollection(display_verts, facecolors=display_colors, edgecolors='black', linewidths=0.5, alpha=0.5)
    ax.add_collection(col)

    ax.autoscale(enable=True, axis='both', tight=True)
    default_title = f"Right Click to Center the {user_mag}x SEM Image Bounding Box--Zoom with Left Click"
    ax.set_title(default_title)

    toolbar = fig.canvas.manager.toolbar
    # Add crosshair cursor
    #cursor = Cursor(ax, useblit=True, color='red', linewidth=0.75)
    sem_box = patches.Rectangle((0, 0), fov_x, fov_y, linewidth=1.5, edgecolor='blue', facecolor='none', linestyle='--')
    ax.add_patch(sem_box)

    #Location variables
    current_cx = 0.0
    current_cy = 0.0
    fixed_fov_x = fov_x
    fixed_fov_y = fov_y
    cid_move = None 
    final_x_grid, final_y_grid = None, None

    #Widgets
    ax_box_x = plt.axes([0.15, 0.14, 0.22, 0.04])   # X TextBox
    ax_box_y = plt.axes([0.58, 0.14, 0.22, 0.04])   # Y TextBox
    ax_btn_re = plt.axes([0.22, 0.04, 0.25, 0.05])   # Reset Button 
    ax_btn_co = plt.axes([0.53, 0.04, 0.25, 0.05])   # Confirm Button

    text_box_x = TextBox(ax_box_x, 'X Center (nm): ', initial="0.0")
    text_box_y = TextBox(ax_box_y, 'Y Center (nm): ', initial="0.0")
    btn_reset   = Button(ax_btn_re, 'Reset & Try Again', color='lightcoral', hovercolor='red')
    btn_confirm = Button(ax_btn_co, 'Confirm Coordinates', color='lightgreen', hovercolor='lime')

    def wrap_toolbar_tool(original_tool_func):
        def wrapper(*args, **kwargs):
            original_tool_func(*args, **kwargs)
            if toolbar.mode == '':
                ax.set_title(default_title)
                fig.canvas.draw_idle()
        return wrapper


    toolbar.zoom = wrap_toolbar_tool(toolbar.zoom)
    toolbar.pan = wrap_toolbar_tool(toolbar.pan)

    first_sub = True   #flag to prevent y value to = 0

    def on_move(event):
        nonlocal toolbar
        if toolbar.mode == '' and ax.get_title() != default_title and cid_move is not None:
            ax.set_title(default_title)
            fig.canvas.draw_idle()
        elif toolbar.mode != '' and ax.get_title() == default_title and cid_move is not None: 
            ax.set_title(f"Please exit the toolbar mode ({toolbar.mode}) to select SEM box location.")
            fig.canvas.draw_idle()

        # Hide the frame if the cursor slips out of the plotting area
        if event.inaxes != ax:
            sem_box.set_visible(False)
            fig.canvas.draw_idle() # Refreshes the display smoothly without lag
            return

        # Center the box bounds directly onto your mouse tip
        cx, cy = event.xdata, event.ydata
        sem_box.set_xy((cx - fov_x / 2, cy - fov_y / 2))
        sem_box.set_visible(True)
        
        # Request an optimized graphical update cycle
        fig.canvas.draw_idle()

    # Click event handler
    def on_click(event):
        nonlocal current_cx, current_cy, cid_move, toolbar
        if event.inaxes != ax:
            return
        
        if toolbar.mode != '':
            return  
            
        # Right-click (button==3) locks the box onto the point and populates the text boxes
        if event.button == 3 and cid_move is not None:
            current_cx = event.xdata
            current_cy = event.ydata
            # Lock the rectangle patch visibly onto the screen at this specific right-click location
            sem_box.set_xy((current_cx - fixed_fov_x / 2, current_cy - fixed_fov_y / 2))
            sem_box.set_visible(True)
            
            # Disconnect the mouse hover loop so the box stops moving when you move toward the inputs
            fig.canvas.mpl_disconnect(cid_move)
            cid_move = None

            text_box_x.disconnect(cid_text_x)
            text_box_y.disconnect(cid_text_y)
            # Populate the interactive entry text boxes with the precise coordinates clicked
            text_box_x.set_val(f"{current_cx:.2f}")
            text_box_y.set_val(f"{current_cy:.2f}")
            first_sub = False
            reconnect_text_events()
            
            ax.set_title(f"Selected image coordinates: {current_cx:.2f}, {current_cy:.2f} -- Adjust and Confirm Below")
            fig.canvas.draw_idle()

    def on_submit(text_val):
        nonlocal current_cx, current_cy
        if cid_move is None:
            try:
                current_cx = float(text_box_x.text)
                if not first_sub:
                    current_cy = float(text_box_y.text)
                sem_box.set_xy((current_cx - fixed_fov_x / 2, current_cy - fixed_fov_y / 2))
                fig.canvas.draw_idle()
            except ValueError:
                pass  # Ignore invalid numbers while user is actively typing

    def on_text_change(text_val):
        nonlocal current_cx, current_cy
        if cid_move is None:
            try:
                current_cx = float(text_box_x.text)
                current_cy = float(text_box_y.text)
                sem_box.set_xy((current_cx - fixed_fov_x / 2, current_cy - fixed_fov_y / 2))
                fig.canvas.draw_idle()
            except ValueError:
                pass 
    def on_reset(event):
        nonlocal cid_move, current_cx, current_cy
        # If it is already unfrozen and tracing, do nothing
        if cid_move is not None:
            return
            
        current_cx = 0.0
        current_cy = 0.0
        
        text_box_x.disconnect(cid_text_x)
        text_box_y.disconnect(cid_text_y)
        text_box_x.set_val("")
        text_box_y.set_val("")
        reconnect_text_events()
        
        #Re-enable the movement tracking and save the new ID back into cid_move
        cid_move = fig.canvas.mpl_connect('motion_notify_event', on_move)
        
        ax.set_title(f"Right Click to Center the {user_mag}x SEM Image Bounding Box--Zoom with Left Click, Hover to see SEM Box")
        fig.canvas.draw_idle()

    def on_confirm(event):
        nonlocal current_cx, current_cy, final_x_grid, final_y_grid, cid_move, cid_close
        if cid_move is not None:
            ax.set_title("ERROR: You must Right-Click to select a location before confirming", color = "red")
            fig.canvas.draw_idle()
            return
        print(current_cx, current_cy)
        print(text_box_x.text, text_box_y.text)
        # if current_cx != float(text_box_x.text) | (current_cy != float(text_box_x.text)):
        #     ax.set_title("WARNING: Current X and Y Values are not saved. Press enter in the text book to save", color = "orange")
        #     fig.canvas.draw_idle()
        #     return

        try:
            current_cx = float(text_box_x.text)
            current_cy = float(text_box_y.text)
        except ValueError:
            ax.set_title("ERROR: Please enter valid numbers in the X and Y boxes", color = "red")
            fig.canvas.draw_idle()
            return
        # Calculate physical linspace boundaries based strictly on locked dimensions
        x_min = current_cx - (fixed_fov_x / 2)
        x_max = current_cx + (fixed_fov_x / 2)
        y_min = current_cy - (fixed_fov_y / 2)
        y_max = current_cy + (fixed_fov_y / 2)
        
        print(f"\nGenerated Scan Grid for Center Point ({current_cx:.2f}, {current_cy:.2f}):")
        print(f"xpx = np.linspace({x_min:.2f}, {x_max:.2f}, 1024)")
        print(f"ypx = np.linspace({y_min:.2f}, {y_max:.2f}, 768)")
        final_x_grid = np.linspace(x_min, x_max, 1024)
        final_y_grid = np.linspace(y_min, y_max, 768)
        fig.canvas.mpl_disconnect(cid_close)
        plt.close(fig) 

    def on_confirm_click(event):
        fig.canvas.mpl_disconnect(cid_close) 
        on_confirm(event)

    def on_window_close(event):
        print("\n[INFO] Layout window closed by user. Terminating script.")
        sys.exit()

    def reconnect_text_events():
        nonlocal cid_text_x, cid_text_y
        cid_text_x = text_box_x.on_text_change(on_text_change)
        cid_text_y = text_box_y.on_text_change(on_text_change)

    # Bind actions
    cid_move = fig.canvas.mpl_connect('motion_notify_event', on_move)
    fig.canvas.mpl_connect('button_press_event', on_click)

    text_box_x.on_submit(on_submit)
    text_box_y.on_submit(on_submit)
    btn_reset.on_clicked(on_reset)
    btn_confirm.on_clicked(on_confirm)

    cid_text_x = None
    cid_text_y = None
    reconnect_text_events()

    cid_close = fig.canvas.mpl_connect('close_event', on_window_close)

    plt.show()

    return final_x_grid, final_y_grid


if __name__ == "__main__":
   
    if len(sys.argv) > 1:
        base_name = os.path.splitext(os.path.basename(sys.argv[1]))[0]
        # Ask for a temporary testing magnification
        user_mag = 50000 
        
        # Test the function standalone
        x_grid, y_grid = plottri(base_name)
    else:
        print("Error: No file entered")
        sys.exit()


