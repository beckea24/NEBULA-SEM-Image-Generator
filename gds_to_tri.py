#To do:
#Ensure that it works?? Properly generates tri but sem image did not turn out
#Have only generate tri for area of scan
    


import os
import sys
import getpass 
import numpy as np
import trimesh
import subprocess
import shapely
import gdspy
from shapely.geometry import Polygon, MultiPolygon, MultiPoint
from shapely.ops import triangulate, unary_union
from triplot import plottri

# Initializations ------------------
#Working directory
current_working_dir = os.getcwd()

#Windows home
username = getpass.getuser()
initial_path = f"C:\\Users\\{username}\\Downloads"
# PowerShell script to open the real Windows file dialog
powershell_cmd = f"""
Add-Type -AssemblyName System.Windows.Forms;
$f = New-Object System.Windows.Forms.OpenFileDialog;
$f.InitialDirectory = '{initial_path}';
$f.Filter = 'GDS Files (*.gds)|*.gds|All Files (*.*)|*.*';
$f.Title = 'Select a GDS File to Open';
$f.MultiSelect = $false;
if ($f.ShowDialog() -eq 'OK') {{ $f.FileName }}
"""

#Functions
def generate_substrate_walls(sub_x, sub_y, sub_z):
    rows = []
    wx = sub_x / 2.0
    wy = sub_y / 2.0
    z_min = -sub_z
    z_max = 0.0  # Top surface
    
    # Material properties for outer substrate boundaries
    mat_in, mat_out = 0, -123
    
    # Helper to format a triangle row with proper normal direction
    def fmt(p1, p2, p3):
        return (f"{mat_in} {mat_out} "
                f"{p1[0]:.6f} {p1[1]:.6f} {p1[2]:.6f} "
                f"{p2[0]:.6f} {p2[1]:.6f} {p2[2]:.6f} "
                f"{p3[0]:.6f} {p3[1]:.6f} {p3[2]:.6f}\n")

    # 1. Bottom Face (Z = z_min) - Normals point down
    rows.append(fmt([-wx, -wy, z_min], [-wx, wy, z_min], [wx, wy, z_min]))
    rows.append(fmt([-wx, -wy, z_min], [wx, wy, z_min], [wx, -wy, z_min]))
    
    # 2. Front Wall (Y = -wy) - Normals point forward
    rows.append(fmt([-wx, -wy, z_min], [wx, -wy, z_min], [wx, -wy, z_max]))
    rows.append(fmt([-wx, -wy, z_min], [wx, -wy, z_max], [-wx, -wy, z_max]))
    
    # 3. Back Wall (Y = wy) - Normals point backward
    rows.append(fmt([-wx, wy, z_min], [-wx, wy, z_max], [wx, wy, z_max]))
    rows.append(fmt([-wx, wy, z_min], [wx, wy, z_max], [wx, wy, z_min]))
    
    # 4. Left Wall (X = -wx) - Normals point left
    rows.append(fmt([-wx, -wy, z_min], [-wx, -wy, z_max], [-wx, wy, z_max]))
    rows.append(fmt([-wx, -wy, z_min], [-wx, wy, z_max], [-wx, wy, z_min]))
    
    # 5. Right Wall (X = wx) - Normals point right
    rows.append(fmt([wx, -wy, z_min], [wx, wy, z_min], [wx, wy, z_max]))
    rows.append(fmt([wx, -wy, z_min], [wx, wy, z_max], [wx, -wy, z_max]))
    
    return rows

def generate_solid_substrate_floor(sub_x, sub_y, mesh_vertices_nm):
    floor_rows = []
    
    # 1. Find the exact outer boundaries of the feature footprint at Z=0
    floor_mask = np.isclose(mesh_vertices_nm[:, 2], 0.0, atol=1e-3)
    floor_vertices = mesh_vertices_nm[floor_mask]
    
    # Feature boundaries
    f_xmin, f_ymin = floor_vertices[:, 0].min(), floor_vertices[:, 1].min()
    f_xmax, f_ymax = floor_vertices[:, 0].max(), floor_vertices[:, 1].max()
    
    # Substrate boundaries
    s_xmin, s_ymin = -sub_x / 2.0, -sub_y / 2.0
    s_xmax, s_ymax = sub_x / 2.0, sub_y / 2.0
    
    # Helper to generate 2 triangles for a flat rectangular section pointing UP (+Z)
    def add_flat_rect(x_min, x_max, y_min, y_max, mat_in, mat_out):
        return [
            f"{mat_in} {mat_out} {x_min:.6f} {y_min:.6f} 0.000000 {x_max:.6f} {y_min:.6f} 0.000000 {x_max:.6f} {y_max:.6f} 0.000000\n",
            f"{mat_in} {mat_out} {x_min:.6f} {y_min:.6f} 0.000000 {x_max:.6f} {y_max:.6f} 0.000000 {x_min:.6f} {y_max:.6f} 0.000000\n"
        ]

    # AREA A: The Feature Interface Patch (Matches lines 3-4 of example)
    #floor_rows.extend(add_flat_rect(f_xmin, f_xmax, f_ymin, f_ymax, 0, 1))
    
    # AREA B: Outer Borders - Vacuum Interface Patches (Matches lines 1-2 of example)
    # Front border (below the feature in Y)
    # if f_ymin > s_ymin:
    #     floor_rows.extend(add_flat_rect(s_xmin, s_xmax, s_ymin, f_ymin, 0, -123))
    # # Back border (above the feature in Y)
    # if s_ymax > f_ymax:
    #     floor_rows.extend(add_flat_rect(s_xmin, s_xmax, f_ymax, s_ymax, 0, -123))
    # # Left border (to the left of the feature in X, restricted to feature Y height)
    # if f_xmin > s_xmin:
    #     floor_rows.extend(add_flat_rect(s_xmin, f_xmin, f_ymin, f_ymax, 0, -123))
    # # Right border (to the right of the feature in X, restricted to feature Y height)
    # if s_xmax > f_xmax:
    #     floor_rows.extend(add_flat_rect(f_xmax, s_xmax, f_ymin, f_ymax, 0, -123))
    
    floor_rows.extend(add_flat_rect(s_xmin, s_xmax, s_ymin, s_ymax, 0, -123))
    return floor_rows

def generate_detector_plane(sub_x, sub_y, detector_z):
    wx = sub_x / 2.0
    wy = sub_y / 2.0
    mat_id = -125  # Matches your example layout rule
    
    # Returns 2 flat triangles pointing UP (+Z direction)
    return [
        f"{mat_id} {mat_id} {-wx:.6f} {-wy:.6f} {detector_z:.6f} {wx:.6f} {-wy:.6f} {detector_z:.6f} {wx:.6f} {wy:.6f} {detector_z:.6f}\n",
        f"{mat_id} {mat_id} {-wx:.6f} {-wy:.6f} {detector_z:.6f} {wx:.6f} {wy:.6f} {detector_z:.6f} {-wx:.6f} {wy:.6f} {detector_z:.6f}\n"
        #-z direction
        ]

def generate_terminator_plane(sub_x, sub_y, sub_z):
    wx = sub_x / 2.0
    wy = sub_y / 2.0
    terminator_z = sub_z-10000 # Sits 10,000nm from the bottom of the substrate
    mat_id = -127          # Matches your example layout rule
    
    # Returns 2 flat triangles pointing UP (+Z direction) to match the template orientation
    return [
        f"{mat_id} {mat_id} {-wx:.6f} {-wy:.6f} {terminator_z:.6f} {wx:.6f} {wy:.6f} {terminator_z:.6f} {wx:.6f} {-wy:.6f} {terminator_z:.6f}\n",
        f"{mat_id} {mat_id} {-wx:.6f} {-wy:.6f} {terminator_z:.6f} {-wx:.6f} {wy:.6f} {terminator_z:.6f} {wx:.6f} {wy:.6f} {terminator_z:.6f}\n"
    ]

def generate_mirror_walls(sub_x, sub_y, sub_z, detector_z):
    rows = []
    wx = sub_x / 2.0
    wy = sub_y / 2.0
    z_min = sub_z-10000    # Starts at the terminator floor
    z_max = detector_z # Ends at the detector ceiling
    mat_id = -122      # Mirror material index
    
    # Helper to quickly format two triangles for a vertical wall section
    def fmt_wall(p1, p2, p3, p4):
        return [
            f"{mat_id} {mat_id} {p1[0]:.6f} {p1[1]:.6f} {p1[2]:.6f} {p2[0]:.6f} {p2[1]:.6f} {p2[2]:.6f} {p3[0]:.6f} {p3[1]:.6f} {p3[2]:.6f}\n",
            f"{mat_id} {mat_id} {p1[0]:.6f} {p1[1]:.6f} {p1[2]:.6f} {p3[0]:.6f} {p3[1]:.6f} {p3[2]:.6f} {p4[0]:.6f} {p4[1]:.6f} {p4[2]:.6f}\n"
        ]

    # 1. Front Mirror Wall (at Y = -wy)
    rows.extend(fmt_wall([-wx, -wy, z_min], [wx, -wy, z_min], [wx, -wy, z_max], [-wx, -wy, z_max]))
    
    # 2. Back Mirror Wall (at Y = wy)
    rows.extend(fmt_wall([-wx, wy, z_min], [-wx, wy, z_max], [wx, wy, z_max], [wx, wy, z_min]))
    
    # 3. Left Mirror Wall (at X = -wx)
    rows.extend(fmt_wall([-wx, -wy, z_min], [-wx, -wy, z_max], [-wx, wy, z_max], [-wx, wy, z_min]))
    
    # 4. Right Mirror Wall (at X = wx)
    rows.extend(fmt_wall([wx, -wy, z_min], [wx, wy, z_min], [wx, wy, z_max], [wx, -wy, z_max]))
    
    return rows

# Paths
try:
    # powershell.exe from inside Linux to run the window
    print("Opening Windows File Explorer...")
    raw_path = subprocess.check_output([
        "powershell.exe", "-NoProfile", "-Command", powershell_cmd
    ])
    
    #Clean up the Windows path string
    win_path = raw_path.decode("utf-8").strip()
    
    if win_path:
        # swap all backslashes to forward slashes 
        win_path_clean = win_path.replace("\\", "/")
        
        # check for the Linux network share prefix
        if win_path_clean.startswith("//wsl.localhost/"):
            parts = win_path_clean.split('/', 4)
            linux_path = "/" + parts[4]
        else:
            #Standard conversion if native Windows file
            linux_path = win_path_clean.replace("C:", "/mnt/c")        
        INPUT_GDS = linux_path
        print(f"Selected file path: {INPUT_GDS}")
        
except Exception as e:
    print(f"Error opening file dialog: {e}")
    INPUT_GDS = None


if INPUT_GDS and os.path.isfile(INPUT_GDS):
    print("File found! Proceeding with processing...")
else:
    print(f"Error: '{INPUT_GDS}' not found.")
    sys.exit(1)

# Vertices Creation 
try:
    print("Loading GDS file and extracting geometry...")
    gds_lib = gdspy.GdsLibrary(infile=INPUT_GDS)
    top_cell = gds_lib.top_level()[0]
    
    # Extract all polygons from the top cell (ignoring specific layers for now)
    all_polys = top_cell.get_polygons(by_spec=False)
    
    if not all_polys:
        print("Error: No polygons found in the selected GDS file.")
        sys.exit(1)

    # Convert gdspy polygons to Shapely polygons
    shapely_polys = [Polygon(p) for p in all_polys]
    
    # Merge overlapping polygons to create one clean footprint
    merged_poly = unary_union(shapely_polys)

    #ask the user for the 3D thickness to extrude it
    while True:
        try:
            feature_z_thickness = float(input("Enter feature thickness to extrude the GDS (in nm): "))
            if feature_z_thickness <= 0:
                print("Error: Thickness must be greater than zero.")
                continue
            break
        except ValueError:
            print("Error: Please enter a valid number.")

    print(f"Extruding 2D GDS footprint to {feature_z_thickness} nm 3D mesh...")

    # Convert the 2D footprint into a 3D trimesh
    if merged_poly.geom_type == 'Polygon':
        mesh = trimesh.creation.extrude_polygon(merged_poly, height=feature_z_thickness)
    elif merged_poly.geom_type == 'MultiPolygon':
        # If there are multiple disconnected shapes, extrude them all and combine
        meshes = [trimesh.creation.extrude_polygon(p, height=feature_z_thickness) for p in merged_poly.geoms]
        mesh = trimesh.util.concatenate(meshes)
    else:
        print("Error: Unrecognized geometry type from GDS.")
        sys.exit(1)

    mesh.process(validate=True)
    mesh.remove_infinite_values() 
    
    # unit conversion scaling factor
    # millimeters (mm) to nanometers (nm) 1000000
    scaling = 1000.0 #microns to nm
    vertices_nm = mesh.vertices * scaling

    # absolute minimum and maximum coordinates
    # edges of the 3D bounding box
    min_bounds = vertices_nm.min(axis=0)  # [min_x, min_y, min_z]
    max_bounds = vertices_nm.max(axis=0)  # [max_x, max_y, max_z]

    # total size along each axis
    size_x = max_bounds[0] - min_bounds[0]
    size_y = max_bounds[1] - min_bounds[1]
    size_z = max_bounds[2] - min_bounds[2]

    #current center point of the feature
    center_x = (min_bounds[0] + max_bounds[0]) / 2.0
    center_y = (min_bounds[1] + max_bounds[1]) / 2.0
    center_z = (min_bounds[2] + max_bounds[2]) / 2.0


    print("STL FEATURE ANALYSIS (in nm)")
    print("Current Bounding Box Edges:")
    print(f"  X: {min_bounds[0]:,.2f} nm to {max_bounds[0]:,.2f} nm")
    print(f"  Y: {min_bounds[1]:,.2f} nm to {max_bounds[1]:,.2f} nm")
    print(f"  Z: {min_bounds[2]:,.2f} nm to {max_bounds[2]:,.2f} nm")
    print(f"Width  (X-Axis Size): {size_x:,.2f} nm")
    print(f"Length (Y-Axis Size): {size_y:,.2f} nm")
    print(f"Height (Z-Axis Size): {size_z:,.2f} nm")
    print("Current Center Location:")
    print(f"  (X: {center_x:,.2f}, Y: {center_y:,.2f}, Z: {center_z:,.2f})")

    #Substrate Box dimensions
    print("Substrate Configuration")
    while True:
        try:
            sub_x = float(input("Enter target Substrate X width (in nm): "))
            sub_y = float(input("Enter target Substrate Y length (in nm): "))
            sub_z = float(input("Enter target Substrate Z thickness (in nm): "))
            
            if sub_x <= 0 or sub_y <= 0 or sub_z <= 0:
                print("Error: Dimensions must be greater than zero. Try again.")
                continue
            break
        except ValueError:
            print("Error: Please enter a valid number.")

    # Confirming the inputs
    print(f"\nConfiguring simulation space to a {sub_x} x {sub_y} nm arena...")
    
    # Calculate the shifts needed
    shift_x = -center_x
    shift_y = -center_y
    shift_z = -min_bounds[2]  # Aligns the bottom of the feature to Z = 0

    print(f"Centering feature to coordinates... (Shifting X: {shift_x:.2f}, Y: {shift_y:.2f}, Z: {shift_z:.2f})")
    # Apply the shift directly to the trimesh vertices array so all faces move together
    mesh.vertices = mesh.vertices + [shift_x / scaling, shift_y / scaling, shift_z / scaling]
    
    # Output Path
    stl_filename = os.path.basename(INPUT_GDS)
    file_name_without_ext, _ = os.path.splitext(stl_filename)
    output_tri_path = os.path.join(current_working_dir, f"{file_name_without_ext}.tri")

    raw_floor_z = mesh.vertices[:, 2].min()


    # Find every unique vertex index that sits on that exact floor boundary
    # We use a safer, slightly larger structural tolerance here
    floor_vertex_indices = np.where(np.isclose(mesh.vertices[:, 2], raw_floor_z, atol=1e-4))[0]

    #Rows for file
    all_simulation_rows = []

    # Use 'enumerate' to track the explicit face positions
    for idx, facet in enumerate(mesh.triangles):
        
        # Pull the 3 vertex indexing IDs belonging to this specific triangle face
        face_vertex_ids = mesh.faces[idx]
        
        # # Check if ALL 3 vertex IDs are part of our pre-mapped floor boundary list
        # on_substrate_surface = np.all(np.isin(face_vertex_ids, floor_vertex_indices))
        
        # # 4. If it matches, skip it! The solid substrate function completely handles this
        # if on_substrate_surface:
        #     continue
            
        # 5. Otherwise, safely scale the walls and features out to the vacuum chamber
        v1, v2, v3 = facet * scaling
        mat_in = 1
        mat_out = -123  # Exposed walls look out into the vacuum environment
            
        all_simulation_rows.append(
            f"{mat_in} {mat_out} "
            f"{v1[0]:.6f} {v1[1]:.6f} {v1[2]:.6f} "
            f"{v2[0]:.6f} {v2[1]:.6f} {v2[2]:.6f} "
            f"{v3[0]:.6f} {v3[1]:.6f} {v3[2]:.6f}\n"
        )


    #substrate walls and bottom
    substrate_walls = generate_substrate_walls(sub_x, sub_y, sub_z)
    all_simulation_rows.extend(substrate_walls)

    #substrate floor surface
    centered_vertices_nm = mesh.vertices * scaling
    exposed_floor = generate_solid_substrate_floor(sub_x, sub_y, centered_vertices_nm)
    all_simulation_rows.extend(exposed_floor)

    #Detector Creation
    while True:
        try:
            working_dist = float(input("Enter Detector Working Distance (in nm above highest feature): "))
            if working_dist <= 0:
                print("❌ Error: Working distance must be greater than zero. Try again.")
                continue
            break
        except ValueError:
            print("❌ Error: Please enter a valid number.")

    highest_feature_z = max_bounds[2] + shift_z
    detector_z = highest_feature_z + working_dist

    detector_plane = generate_detector_plane(sub_x, sub_y, detector_z)
    all_simulation_rows.extend(detector_plane)

    #Terminator Creation
    terminator_plane = generate_terminator_plane(sub_x, sub_y, sub_z)
    all_simulation_rows.extend(terminator_plane)    
    
    #Mirror Wall Creation
    mirror_walls = generate_mirror_walls(sub_x, sub_y, sub_z, detector_z)
    all_simulation_rows.extend(mirror_walls)

    # Triangle Data write
    print(f"Converting and writing faces to: {output_tri_path}")
    # Write all compiled simulation rows directly to the file
    with open(output_tri_path, 'w') as tri_file:
        tri_file.writelines(all_simulation_rows)
            
    print("✅ Success! The stl and substrate have been converted to .tri.")
    print(f"Your .pri beam 'z' must be between: {highest_feature_z:,.2f} and {detector_z:,.2f} nm")
    print(f"""\nRun:
        \npython pri_gen.py {file_name_without_ext}
        \nnebula_cpu_mt {file_name_without_ext}.tri {file_name_without_ext}.pri substrate.mat feature.mat > {file_name_without_ext}.det
        """)
        
except Exception as e:
    print(f"Error during geometric file processing: {e}")