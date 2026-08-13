import os
import sys
import getpass 
import subprocess
import gdsfactory as gf
from gdsfactory.technology import LayerStack, LayerLevel

# Activate the generic PDK
gf.gpdk.PDK.activate()

# Load your existing GDS
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
    print("File found.")
else:
    print(f"Error: '{INPUT_GDS}' not found.")
    sys.exit(1)


c = gf.import_gds(INPUT_GDS)
gds_filename = os.path.basename(INPUT_GDS)
file_name_without_ext, _ = os.path.splitext(gds_filename)
# Define your layer stack
layer_stack = LayerStack(
    layers={ 
        "silicon_substrate": LayerLevel( #substrate layer doesn't affect anything
            layer=(0, 0),
            thickness=0.250,
            zmin=0.0,
            material="si", #doesn't matter
        ),
        "hsq_waveguide": LayerLevel( #actual layer thickness of the waveguide. 
        #This code only works for single thickness gds
            layer=(1, 0),
            thickness=0.054,
            zmin=0.250,
            material="sio2", 
        ),
    }
)

# Export to STL
gf.export.to_stl(c, f"{file_name_without_ext}.stl", layer_stack=layer_stack)
print( "STL file created.")