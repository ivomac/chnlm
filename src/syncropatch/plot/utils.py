
import os
from pathlib import Path
import matplotlib.pyplot as plt
import nwb
import numpy as np
from typing import Union
import math

def is_bad_rep(rep):
    rSeal = rep.get("seal").mean()
    rseries = rep.get("r_series").mean()
    CSlow   = rep.get("capacitance_slow").mean()
    if(np.isnan(rSeal) or np.isnan(rseries) or np.isnan(CSlow)):
      return True
    if ((rSeal< 100) or (rseries>20)):
        return True
    else:
        return False
    

def create_tmp_images(rcell_folder: str, stimulus_name: str, rep_id: Union[str, int], img_folder:Path):
    nwb.plot.style("monospace")
    rcell_folder = Path(rcell_folder)
    expName = Path(rcell_folder).stem
    output_folder = Path(img_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    file_list = rcell_folder.glob('*.nwb')
    
    for f in file_list:
        print(f, stimulus_name, rep_id)
        rcell = nwb.RCell(f)
        rep = rcell.prt(stimulus_name).rep(rep_id)
        expName = Path(f).stem 
        fig = rep.plot().fig
        if is_bad_rep(rep):
            #fig.figure.text(0,1e-9, 'Bad Cell')
            for line in fig.figure.gca().get_lines():
                line.set_color("0.95")
        #print(f"cellName [{expName}] RSeal = {rSeal}  Cm = {CSlow} Rseries = {rseries}")
        filename = output_folder / ( expName+ '_' + stimulus_name + '_rep' + str(rep_id) + '_tmp.png')
        #print(output_folder / filename)
        plt.savefig(filename, dpi=100)
        #plt.gcf().clear
        plt.close()
    #rcell_folder = '/Users/escantam/Desktop/Processing/240513_004_CL1'
    #stimulus_name = 'Activation'
    
    #html_filename = os.path.join(img_folder, (expName + '.html')) 
   # title = expName
   # print_html_by_folder(output_folder, html_filename, title, nRow, nCol)



def print_html_by_folder(folder_or_image_paths: Path, nRows: int, nCols: int,
                         file_to_save: Path, startID:int=0, page_title: str = ''):
    if folder_or_image_paths.is_dir(): 
        image_paths = list(Path(folder_or_image_paths).glob('*.png'))
    else:
        image_paths = folder_or_image_paths
    return _generate_html(
        image_paths=image_paths,
        nRows=nRows,
        nCols=nCols,
        file_to_save=file_to_save,
        startID=startID,
        page_title=page_title
    )


def _generate_html(image_paths: list, nRows: int, nCols:int, file_to_save: Path, startID:int=0,  page_title: str = ''):

    html_header = ''
    html_header += '<html> \n'
    html_header += '<head> <title>' + page_title + '</title> </head> \n'
    html_header += '<body style="text-align:center"> \n'
    html_header += '<div style="display:inline-block; position:relative; min-width: 700px;"> \n' # need position:relative to properly place the link to IC list
    html_header += '<h2>' + page_title + '</h2> \n'

    html_footer = ''
    html_footer += '<br> \n'
    html_footer += '</div> \n'
    html_footer += '</body> \n'
    html_footer += '</html> \n'

    html_plots = _generate_html_plots(image_paths=image_paths, nRows=nRows, nCols=nCols, startID=startID);

    with open(file_to_save, "w") as f:
         print(html_header, file=f)
         print(html_plots, file=f)
         print(html_footer, file=f)


def _generate_html_plots(image_paths: list, nRows:int, nCols:int, startID=0):
    #ncols = 2  # images per row
    ncells = len(image_paths);
    html = '<table border="1"> \n'
    cnt = 0
    #nrows = 16
    cnt = 0
    imgFileName = Path(image_paths[0]).stem
    imgPath     = str(Path(image_paths[0]).parent)
    imgDirName  = Path(image_paths[0]).parent.stem
    tokens      = imgFileName.split('_') 
    for i in range(nRows):
        html += '<tr> \n'
        for j in range(nCols):
            colOffset = math.floor(startID/16)
            well_name = chr(65+i) + str(j+1+colOffset)
            tokens[3] = well_name
            #fileName = imgPath + "/" + "_".join(tokens) + '.png'
            fileName = "./" + imgDirName + "/" + "_".join(tokens) + '.png'
            #print(f"nRow = {i}, nCol ={j}")
            html += '<td style="max-width:500px"> \n'
            html += '<a href="' + fileName + '"> \n'
            html += '<img width="100%" src="' + fileName + '">'
            html += '</a> \n'
            html += '</td> \n'
            cnt = cnt + 1
            if cnt >= ncells:
                break
        html += '</tr> \n'
    html += '</table> \n'
    html += '<br> \n'
    return html
