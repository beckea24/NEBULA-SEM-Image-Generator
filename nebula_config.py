#Run all three sections of nebula code
#Notes: does not support MacOS, or selecting from a drive other than C: (can select wsl files)
from stl_convert import generate_tri #converts STL to .tri
from pri_gen import generate_pri   #Generates .pri file from .tri
from sem_gen import generate_sem   #Generates SEM image from .det
import os
import sys
import getpass 
import subprocess
import numpy as np

#Functions

def find_file(file_extension):
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
    $f.Filter = '{file_extension.upper()} Files (*{file_extension})|*{file_extension}|All Files (*.*)|*.*';
    $f.Title = 'Select a {file_extension.upper()} File to Open';
    $f.MultiSelect = $false;
    if ($f.ShowDialog() -eq 'OK') {{ $f.FileName }}
    """

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
            INPUT = linux_path
            print(f"Selected file path: {INPUT}")
            
    except Exception as e:
        print(f"Error opening file dialog: {e}")
        INPUT = None


    if INPUT and os.path.isfile(INPUT) and INPUT.lower().endswith(file_extension):
        return INPUT
    else:
        print(f"Error: '{INPUT}' not found.")
        sys.exit(1)


#If existing, allow user to import .tri, .pri, and .det files
print("Welcome to the Nebula SEM Image Generator!")
help = input("Help? [y/n]: ")

if help.lower() == 'y':
    print("***")
    print("This program will generate an SEM image based on a provided STL file (typically generated from a GDS file).")
    print("You can also import existing .tri, .pri, and .det files if you have them. The program will continue from there.")
    print("")
    print("Note: If you import a .det file, you do not need to import .tri or .pri files, as the .det file contains all the necessary information.")
    print("***")
print("If you have existing .tri, .pri, or .det files, you can import them now.")
print("Otherwise, the program will generate them from your STL file.")
input_check = input("\n\x1B[3m I have .tri, .pri, or .det files\x1b[0m] [y/n]:")

tri_file, pri_file, det_file = None, None, None

if input_check.lower() == 'y':
    tri_check = input("Would you like to import a .tri file? [y/n]: ")
    if tri_check.lower() == 'y':
        tri_file = find_file('.tri')
        file_name_without_ext = os.path.splitext(os.path.basename(tri_file))[0]
        change_name = input(f"Would you like to change the output file name from {file_name_without_ext}? [y/n]: ")
        if change_name.lower() == 'y':
            file_name_without_ext = input("Enter the new name for the output files (without extension): ")
        d = np.loadtxt(tri_file)
        z = lambda m: d[np.any(d[:, :2] == m, axis=1), 2:].reshape(-1, 3)[:, 2]
        highest_feature, detector_z = z(1).max(), z(-125).max()
    pri_check = input("Would you like to import a .pri file? [y/n]: ")
    if pri_check.lower() == 'y':
        pri_file = find_file('.pri')
    if pri_file and not tri_file:
        print("Warning: You have imported a .pri file without a .tri file. The program will continue, but will fail if you do not enter a .det file")
        quit = input("Would you like to import a .tri file? [y/n]: ")
        if quit.lower() == 'y':
            tri_file = find_file('.tri')
    det_check = input("Would you like to import a .det file? [y/n]: ")
    if det_check.lower() == 'y':
        det_file = find_file('.det')


#Check if .tri needs to be generated
if tri_file == None  and det_file == None:
    #Generate .tri from STL
    file_name_without_ext = input("Enter the name for the output files (without extension): ")
    print("No .tri file provided. Generating .tri from STL...")
    file_name_without_ext, tri_file, highest_feature, detector_z = generate_tri()

#Check if .pri needs to be generated
if pri_file == None and det_file == None:
    #Generate .pri from .tri
    print("No .pri file provided. Generating .pri from .tri...")
    pri_file = generate_pri(file_name_without_ext, highest_feature, detector_z)

#Check if .det needs to be generated
if det_file == None:

    view_mat = input("Would you like to see a list of the provided materials? [y/n]: ")
    mat_list = ['alumina', 'aluminium', 'copper', 'gold', 'pmma', 'silicon', 'silicondioxide']
    if view_mat.lower() == 'y':
        print("""Alumina   Aluminium   Copper    Gold\nPmma      Silicon     SiliconDioxide """)

    add_new_mat = input("Would you like to add a new material? [y/n]: ")
    if add_new_mat.lower() == 'y':
        #Direct them to nebula documentation for adding new materials to the nebula_config.py file
        #Import new materials
        print("To be implemented")
    while True: 
        substrate_mat = input("Choose your substrate material: ").lower() + ".mat"
        feature_mat = input("Choose your feature material: ").lower() + ".mat"

        sub_check = False
        fet_check = False
        for mat in mat_list:
            if substrate_mat == mat + ".mat":
                sub_check = True
            if feature_mat == mat + ".mat":
                fet_check = True
    
        if not(fet_check or sub_check):
            if not sub_check:
                print("Error: Substrate material is not in material list")
            if not fet_check:
                print("Error: Feature material is not in material list")
            view_mat = input("Would you like to see a list of the provided materials? [y/n]: ")
            if view_mat.lower() == 'y':
                print("""Alumina   Aluminium   Copper    Gold\nPmma      Silicon     SiliconDioxide """)
            continue
        break
    

    #Generate .det from nebula
    current_working_dir = os.getcwd()
    det_file_path = os.path.join(current_working_dir, f"{file_name_without_ext}.det")

    nebula_cmd = [
        "nebula_cpu_mt", 
        tri_file, 
        pri_file, 
        substrate_mat, 
        feature_mat
    ]

    print(f"Running Nebula and saving output to {det_file_path}...")

    try:

        with open(det_file_path, "w") as det_file:
            subprocess.run(nebula_cmd, stdout=det_file, check=True)
        print("Simulation complete.")

    except subprocess.CalledProcessError as e:
        # Triggers if Nebula runs but crashes (e.g., bad inputs, internal error)
        print(f"\n[ERROR] Nebula simulation failed with exit code {e.returncode}.")
        
    except FileNotFoundError as e:
        # Triggers if Python can't find "nebula_cpu_mt" on your system
        print(f"\n[ERROR] Could not find the Nebula executable. Ensure Nebula is installed")
        print(f"Details: {e}")
        
    except PermissionError:
        # Triggers if Docker or WSL doesn't have permission to write to the output folder
        print(f"\n[ERROR] Permission denied. Cannot save to {det_file_path}.")
        
    except Exception as e:
        # A generic catch-all for any other weird system errors
        print(f"\n[ERROR] An unexpected error occurred: {e}")

#Generate SEM image
generate_sem(det_file)
