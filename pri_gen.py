import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor
import matplotlib.patches as patches 
from matplotlib.widgets import TextBox, Button 

from triplot import plottri

def generate_pri(base_name, min_z = None, max_z = None):

    #Output file name and path
    output_pri_name = f"{base_name}.pri"
    output_pri_path = os.path.join(os.getcwd(), output_pri_name)

    z = 55
    if min_z != None and max_z != None:
        while True:
            try:
                print(f"Beam height must be between {round(min_z)} and {round(max_z)}")
                z = float(input("Enter beam height (nm): "))
                
                if z < min_z or z > max_z:
                    print(f"Error: Beam height must be between {min_z} and {max_z}")
                    continue
                break
            except ValueError:
                print("Error: Please enter a valid number.")
    
    xpx, ypx = plottri(base_name)
    # xpx = np.linspace(-11500, -6157.2, 1024)   # x pixels: between -50nm and +50nm, in steps of 1nm
    # ypx = np.linspace(-1996.8, 1996.8,  768)  # y pixels: between -100nm and +100nm, in steps of 1nm
    x_center = 0.0
    y_center = 0.0

    energy = float(input("Enter Beam Energy (in eV): ")) 
    epx = int(input("Enter Number of Electrons per Pixel (=I*tdwell/qe): "))
    sigma = 1                         # Standard deviation of Gaussian beam spot size
    poisson = True                    # Whether to use Poisson shotnoise

        
    # This is a numpy datatype that corresponds to pri files
    electron_dtype = np.dtype([
        ('x',  '=f'), ('y',  '=f'), ('z',  '=f'), # Position
        ('dx', '=f'), ('dy', '=f'), ('dz', '=f'), # Direction
        ('E',  '=f'),                             # Energy
        ('px', '=i'), ('py', '=i')])              # Pixel index

    # Open file in your active working directory
    print(f"Generating binary scan file at: {output_pri_path}")
    with open(output_pri_path, 'wb') as file:
        # Iterate over pixels
        for i, xmid in enumerate(xpx):
            for j, ymid in enumerate(ypx):
                # Number of electrons in this specific pixel
                N_elec = np.random.poisson(epx) if poisson else epx

                # Allocate numpy buffer
                buffer = np.empty(N_elec, dtype=electron_dtype)

                # Fill with data
                buffer['x'] = np.random.normal(xmid, sigma, N_elec)
                buffer['y'] = np.random.normal(ymid, sigma, N_elec)
                buffer['z'] = z
                buffer['dx'] = 0
                buffer['dy'] = 0
                buffer['dz'] = -1
                buffer['E'] = energy
                buffer['px'] = i
                buffer['py'] = j

                # Write buffer to file
                buffer.tofile(file)

    print(f"{output_pri_name} has been generated.")
    return output_pri_path

if __name__ == "__main__":
        #filename passed from the terminal command line
    if len(sys.argv) > 1:
        # Use the name provided (strips any accidentally included extensions)
        base_name = os.path.splitext(os.path.basename(sys.argv[1]))[0]
    
    else:
        # Fallback default name if you run the script with no arguments
        base_name = "pri_file"
    # Call the main function to generate the .pri file
    generate_pri(base_name)