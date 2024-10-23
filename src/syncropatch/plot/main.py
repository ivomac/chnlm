import os
from pathlib import Path
from .utils import create_tmp_images, print_html_by_folder
import h5py

def plot_experiment(nwb_folder: Path = Path(os.getenv("SYNCROPATCH_NWB_PATH")) / "rcell", plot_path: Path = Path(os.getenv("SYNCROPATCH_PLOT_PATH")), overwrite=True):
    rCellFolders = [path for path in nwb_folder.iterdir() if path.is_dir()]
    print(rCellFolders)

    #rCellFolders = [f.path for f in os.scandir(dirSearchPath) if f.is_dir() ]
    #print(f"the directories are {rCellFolders}")
    for rCellDir in rCellFolders:
        #output_folder = Path(os.path.join(img_folder,  (str(expName) + '_plots')))
        exp_name = rCellDir.stem
        tokens = exp_name.split('_')
        cellLine = tokens[-1]
        first_rcell_path = next(rCellDir.glob('*.nwb'))
        with h5py.File(first_rcell_path, "r") as f:
            host_cell = f["general/cell_info/host_cell"]
            species = f["general/cell_info/species"]
            ion_channel = f["general/channel_info/ion_channel"]
            chipCols = f["general/cell_info/chip_cols"][...].item().decode("UTF-8")
            minVal = int(chipCols.split("-")[0])
            maxVal = int(chipCols.split("-")[1])

        HTML_title = f"{exp_name} {host_cell} {species} {ion_channel}"
        imagePath = plot_path /  exp_name.split('_')[0] / '_'.join(exp_name.split('_')[0:2])  / exp_name / (exp_name + '_plots')
        print(rCellDir)
        if overwrite == True:
            create_tmp_images(
                rcell_folder=rCellDir,
                stimulus_name='Activation',
                rep_id=1,
                img_folder=imagePath
            )
        html_filename = plot_path / exp_name.split('_')[0] / '_'.join(exp_name.split('_')[0:2]) / exp_name / (exp_name + '.html')

        nCols = maxVal-minVal+1
        nRows  = 16
        startID = (minVal-1)*nRows
        print_html_by_folder(
            folder_or_image_paths=imagePath,
            nRows=nRows,
            nCols=nCols,
            file_to_save=html_filename,
            startID=startID,
            page_title=HTML_title
        )




