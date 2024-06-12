"""
Notes on this module: 

1. I would have made so many of these functions methods of
a subclass of pathlib.pathlib.Path, but subclassing pathlib.Path is really annoying because
of its "_flavor" attribute, used to differentiate between Posix and Windows 
file systems. Therefore, we have this module with functions that would gladly 
belong in a class. Sigh.

2. All file system functions in this module should support both str parameters
as well as pathlib.pathlib.Path. Generally, this is as easy as converting pathlib.Path objects
to strings using str() or vice versa with pathlib.Path().
"""

import contextlib
import json
import os
import pathlib
import psutil
import shutil
from ast import literal_eval
from configparser import ConfigParser
from enum import Enum

import numpy as np
import skimage.io
from natsort import natsorted
from tifffile import TiffFile


RE_NUM = "[0-9]"


class ImageFileType(Enum):
    """
    Enum class with constants representing image file type, which is determined
    by file extension.

    Current assumptions are that all image file types are supported by 
    skimage's io module, so that imread and imwrite work. If this ends up
    not being the case, separate implementation will need to be applied for 
    those image file extensions that aren't supported.
    """
    TIF: str = [".tif", ".tiff"]
    PNG: str = [".png"]


class OtherFileType(Enum):
    TXT: str = ".txt"


class FileSubtype(Enum):
    """
    Enum class with constants representing file subtype, which is determined
    by substrings in filename, such as "MMStack" for Micro-Manager tif stack 
    images and "metadata" for Micro-Manager metadata files. 
    """
    MMSTACK: str = "MMStack"
    METADATA: str = "metadata"
    LS_NOTES: str = "notes"
    OME: str = ".ome"


#functions to determine file type
def get_file_type(file_path: pathlib.Path) -> ImageFileType:
    """
    Gets file type, determined by file extension.

    ### Paramaters:

    file_path: str

    ### Returns:

    file_type: FileType
        file type of file at file_path.
    """
    file_path = pathlib.Path(file_path)
    file_extn = file_path.suffix
    if file_extn == OtherFileType.TXT.value:
        return OtherFileType.TXT
    for extn in ImageFileType.TIF.value:  
        if file_extn == extn:
            return ImageFileType.TIF
    for extn in ImageFileType.PNG.value:  
        if file_extn == extn:
            return ImageFileType.PNG


def get_file_subtype(file_path: pathlib.Path) -> FileSubtype:
    """
    Gets subtype of file. Subtype is the location/context from where that file
    was generated.

    For example, a file with subtype MMSTACK is a tif stack file generated
    by Micro-Manager.

    ### Parameters:

    file_path: str

    ### Returns:

    file_subtype: FileSubtype
        file subtype of file at file_path.
    """
    file_type = get_file_type(file_path)
    filename = file_path.name
    if file_type == ImageFileType.TIF and FileSubtype.MMSTACK.value in filename:
        return FileSubtype.MMSTACK
    if file_type == OtherFileType.TXT:
        if FileSubtype.METADATA.value in filename:
            return FileSubtype.METADATA
        elif FileSubtype.LS_NOTES.value in filename:
            return FileSubtype.LS_NOTES
        

def is_tif(file_path: pathlib.Path):
    return get_file_type(file_path) == ImageFileType.TIF


def is_png(file_path: pathlib.Path):
    return get_file_type(file_path) == ImageFileType.PNG


def is_mm_metadata(file_path: pathlib.Path):
    return get_file_subtype(file_path) == FileSubtype.METADATA


def is_ls_pycro_notes(file_path: pathlib.Path):
    return get_file_subtype(file_path) == FileSubtype.LS_NOTES


def get_image_extns() -> list:
    """
    Returns list with all image file extensions.
    """
    extn_lists = [extn.value for extn in ImageFileType]
    return [extn for ftype in extn_lists for extn in ftype]


def remove_file_extn(file_path) -> pathlib.Path:
    path = pathlib.Path(file_path)
    path.with_suffix("")
    if isinstance(file_path, str):
        return str(path)
    elif isinstance(file_path, pathlib.Path):
        return path
    

def remove_mmstack(file_path: pathlib.Path) -> pathlib.Path:
    """
    removes "MMStack_" substring from Micro-Manager image filenames.

    If file_path is a str, returns str with "MMStack_" removed. If file_path 
    is a pathlib.Path, instead returns pathlib.Path with "MMStack_" removed.
    """
    file_name = str(file_path).replace(f"_{FileSubtype.MMSTACK.value}", "")
    if isinstance(file_path, str):
        return file_name
    elif isinstance(file_path, pathlib.Path):
        return pathlib.Path(file_name)
    

def remove_ome(file_path: pathlib.Path) -> pathlib.Path:
    """
    removes ".ome" substring from Micro-Manager image filenames.

    If file_path is a str, returns str with ".ome" removed. If file_path 
    is a pathlib.Path, instead returns pathlib.Path with ".ome" removed.
    """
    file_name = str(file_path).replace(FileSubtype.OME.value, "")
    if isinstance(file_path, str):
        return file_name
    elif isinstance(file_path, pathlib.Path):
        return pathlib.Path(file_name)
    

def shutil_copy_ignore_images(source_dir: pathlib.Path, 
                              dest_dir: pathlib.Path
                              ):
    """
    Copies directory tree of root_dir, which includes all folders, subfolders,
    and files within those locations other than PNG and TIF files to dest_dir.

    ## Parameters:

    source_dir: str
        source directory to be copied.
    
    dest_dir: str
        destination directory that source_dir is copied to.
    """
    #*{file_extension} references all files with the given extension in a 
    #directory, so list below creates the ignore pattern to all image file 
    #types set in ImageFileType.
    #* to unpack list into arguments
    ignore_pattern = get_image_ignore_pattern()
    return shutil.copytree(
        source_dir, dest_dir, ignore=ignore_pattern, dirs_exist_ok=True)


def get_image_ignore_pattern():
    ignore_list = [f"*{extn}" for extn in get_image_extns()]
    return shutil.ignore_patterns(*ignore_list)


def file_in_use(file_path: pathlib.Path) -> bool:
    """
    Checks to see if file located at file_path is currently in use by process
    listed in psutil.processess_iter(). If file is in use, returns True. 
    Else, False.
    """
    file_path = str(file_path)
    for process in psutil.process_iter():
        try:
            for item in process.open_files():
                if file_path == item.path:
                    return True
        except Exception:
            pass
    return False


def get_dir_name(dir: pathlib.Path) -> str:
    """
    Returns directory name. If dir is a file path, returns name of parent
    directory.
    """
    dir = pathlib.Path(dir)
    if dir.is_dir():
        return pathlib.Path(dir).name
    elif dir.is_file():
        return pathlib.Path(dir).parent.name
    

def get_batch_path(source_path: pathlib.Path, 
                   dest_dir: pathlib.Path, 
                   suffix: str = ""
                   ) -> pathlib.Path:
    """
    returns save directory for batch processes.

    ### Example:
    >>> get_batch_dest_path("C:/Jonah/foo", "D:/Drake", "_dr")
    >>> 'D:/Drake/foo_dr'
    """
    old_folder_name = get_dir_name(source_path)
    new_folder_name = f"{old_folder_name}{suffix}"
    return pathlib.Path(dest_dir).joinpath(new_folder_name)


def get_save_path(file_path: pathlib.Path, 
                  source_path: pathlib.Path, 
                  dest_path: pathlib.Path,
                  ) -> pathlib.Path:
    """
    Returns file save path for batch processes. 

    ### Example:
    >>> get_save_path("C:/Jonah/fish/pos/foo.tif", "C:/Jonah", "D:/Drake")
    >>> 'D:/Drake/fish/pos/foo.tif'
    """
    rel_path = file_path.relative_to(source_path)
    return dest_path.joinpath(rel_path)
    

def is_other_image_files(file_path: pathlib.Path) -> bool:
    """
    If there are other image files in the parent directory of file_path 
    (according to image file types in ImageFileType class), returns True. 
    Else, returns False.
    """
    file_path = pathlib.Path(file_path)
    for file in file_path.parent.iterdir():
        if file_is_image(file) and not file_path.samefile(file):
            return True
    return False


def get_image_files(dir: pathlib.Path):
    """
    Returns list of all image files in given directory.
    """
    dir_path = pathlib.Path(dir)
    files = []
    for file in dir_path.iterdir():
        with contextlib.suppress(TypeError):
            if file_is_image(file):
                files.append(str(file))
    #natsorted() sorts list so that files are sorted by number subscripts in
    #the correct order. ie, if there are 20 files named "image_1", "image_2",
    #..., order is "image_1", "image_2", ... "image_19" instead of "image_1",
    #"image_10", "image_11", ... "image_2", "image_3", ...
    files = natsorted(files)
    if isinstance(dir, pathlib.Path):
        files = [pathlib.Path(file) for file in files]
    return files


def get_image_lists(source_path: pathlib.Path):
    """
    Returns list of lists of image files in directory and all subdirectories.
    """
    image_lists = []
    for root, directories, filenames in os.walk(source_path):
        image_list = get_image_files(pathlib.Path(root))
        if image_list:
            image_lists.append(image_list)
            print(image_list)
    return image_lists


def get_all_subdirectories(source_path: pathlib.Path):
    subdirectories = []
    for root, dirs, files in os.walk(source_path):
        print(root)
        subdirectories.append(pathlib.Path(root))
    return subdirectories


def copy_non_image_files(source_dir: pathlib.Path, 
                         dest_dir: pathlib.Path):
    """
    Copies non-image files in source_dir to dest_dir
    """
    source_dir = pathlib.Path(source_dir)
    dest_dir = pathlib.Path(dest_dir)
    for file in pathlib.Path(source_dir).iterdir():
        if not file_is_image(file):
            shutil.copy(file, dest_dir)


def read_image(file_path: pathlib.Path) -> np.ndarray:
    """
    reads in images in file and returns them as ndarray.

    This is mostly here because tifffile loads in all images from all image 
    files that share metadata, which hogs memory. If file_path is a tif file,
    this loads in only the images stored in that file.
    """
    if get_file_type(file_path) == ImageFileType.TIF:
        stack = TiffFile(file_path)
        num_pages = len(stack.pages)
        image = stack.asarray(range(num_pages))
    else:
        image = skimage.io.imread(file_path)
    return image


def save_image(save_path: pathlib.Path, 
               image: np.ndarray, 
               png_compression: int = 3):
    if is_png(save_path):
        skimage.io.imsave(
            save_path, image, check_contrast=False, 
            compress_level=png_compression)
    else:
        skimage.io.imsave(save_path, image, check_contrast=False)


def file_is_image(file_path: pathlib.Path) -> bool:
    """
    If file is an image file according to file extensions in ImageFileType
    class, returns True. Else, returns False.
    """
    file_path = pathlib.Path(file_path)
    if file_path.suffix in get_image_extns():
        return True
    else:
        return False


def get_reduced_filename(file_path: pathlib.Path) -> str:
    file_path = pathlib.Path(file_path)
    filename = file_path.name
    filename = filename.split(FileSubtype.OME.value)[0]
    filename = remove_mmstack(filename)
    filename = remove_file_extn(filename)
    return filename


def is_mm(file_path: pathlib.Path):
    try:
        MMMetadata(file_path)
        return True
    except FileNotFoundError:
        return False
    

def from_same_mm_series(file_list) -> bool:
    first_file = file_list[0]
    if is_mm(first_file):
        filenames = MMMetadata(first_file).all_filenames
        for file in file_list[1:]:
            file_path = pathlib.Path(file)
            if file_path.name not in filenames:
                return False
        else:
            return True
    else:
        return False


class MMMetadata(object):
    """
    Class to hold Micro-Manager metadata from Micro-Manager tif stack files.

    ## Constructor Parameters:

    file_path: str
        file path of MM tif image.
    """
    #Possible axes in Micro-Manager metadata
    _Z = "z"
    _CHANNEL = "channel"
    _TIME = "time"
    _POSITION = "position"

    def __init__(self, file_path: pathlib.Path):
        self.file_path = file_path
        self._metadata_dict: dict = self._get_metadata_dict()
        self.summary_metadata: dict = self._metadata_dict["Summary"]
        self.axis_order = self._get_axis_order()
        self.frame_keys: list = [k for k in self._metadata_dict if "FrameKey" in k]
        self.image_width: int = int(self.summary_metadata["Width"])
        self.image_height: int = int(self.summary_metadata["Height"])
        self.dims: dict = self._get_dimensions()
        self.num_dims: int = len(self.dims)
        self.directory = str(pathlib.Path(file_path).parent)
        self.all_filenames: list = self._get_all_filenames()
        self.is_multifile: bool = len(self.all_filenames) > 1

    def get_image_metadata(self, image_num: int):
        return MMImageMetadata(self, image_num)
    
    def get_filename_start_num(self, filename: pathlib.Path):
        filename = pathlib.Path(filename).name
        for key in self.frame_keys:
            meta_filename = self._metadata_dict[key]["FileName"]
            if filename == meta_filename:
                return self.frame_keys.index(key)

    def _get_metadata_dict(self) -> dict:
        file_path = pathlib.Path(self.file_path)
        filename = get_reduced_filename(file_path)
        if file_path.is_file():
            if get_file_type(file_path) in ImageFileType:
                file_path = file_path.parent
        file_generator = file_path.iterdir()
        parent_files = [file for file in file_generator]
        for file in parent_files:
            if is_mm_metadata(file_path) and filename in file.name:
                return json.load(open(file))
        else:
            #If no metadata file is found that matches name of image, assume
            #only one metadata file is in folder that doesn't match name.
            for file in parent_files:
                if is_mm_metadata(file):
                    return json.load(open(file))  
        raise FileNotFoundError("MMMetadata file not found in directory.")

    def _get_axis_order(self):
        axis_order: list = self.summary_metadata["AxisOrder"]
        #Delete position axis because images at different x-y stage positions
        #in MM are saved in different files with different metadata files.
        axis_order.remove(self._POSITION)
        return axis_order

    def _get_dimensions(self) -> dict:
        intended_dims = self.summary_metadata["IntendedDimensions"]
        dims = {}
        for axis in self.axis_order:
            dims[axis] = int(intended_dims[axis])
        return dims

    def _get_all_filenames(self):
        filenames = []
        for key in self.frame_keys:
            filename = self._metadata_dict[key]["FileName"]
            if filename not in filenames:
                filenames.append(filename)
        return filenames
    

class MMImageMetadata(object):
    def __init__(self, mm_metadata: MMMetadata, image_index: int):
        self._mm_metadata: MMMetadata = mm_metadata
        self.image_index: int = image_index
        self.framekey: str = mm_metadata.frame_keys[image_index]
        self.image_metadata: dict = mm_metadata._metadata_dict[self.framekey]
        self.coords: dict = self._get_coords()
        self.pixel_size: float = float(self.image_metadata["PixelSizeUm"])
        self.binning: int = int(self.image_metadata["Binning"])
        self.image_width: int = int(self.image_metadata["ROI"].split("-")[-2])
        self.image_height: int = int(self.image_metadata["ROI"].split("-")[-1]) 
        self.x_pos: float = float(self.image_metadata["XPositionUm"])
        self.y_pos: float = float(self.image_metadata["YPositionUm"])
        self.z_pos: float = float(self.image_metadata["ZPositionUm"])

    def get_coords_str(self):
        coords_str = ""
        for item in self.coords.items():
            coords_str = f"{coords_str}_{item[0]}{item[1]:03d}"
        return coords_str.strip("_")
    
    def _get_coords(self):
        """
        returns dictionary with image coords. ie if the image is from 
        z-slice 21 and taken with channel 2, coords_dict will be 
        {"Z": 20, "C": 1}
        """
        #Since this is meant to represent the same coord information that's 
        #found in each framekey, I originally thought I could just use the 
        #framekey to determine coordinates of each image. However, which 
        #coordinate position in each framekey corresponds to which coordinate 
        #label (C, Z, T, etc.), which one would think would be determined by
        #the "Axis Order" property, isn't consistent (sometimes reverse order,
        #other times not). Instead, coords are determined by an algorithm
        #that matches image index with permutation of dimensions, which
        #correctly aligns with framekey.
        dimensions = self._mm_metadata.dims
        framekey_coords = self._get_framekey_coords()
        coords = {}
        for key in dimensions.keys():
            if dimensions[key] != 1:
                coords[key] = framekey_coords[key]
        return coords
    
    def _get_framekey_coords(self):
        framekey_coords = {}
        framekey_nums = [int(n) for n in self.framekey.split("-")[1:]]
        #Order of framekeys is Framekey-(time)-(channel)-(z)
        framekey_coords[MMMetadata._Z] = framekey_nums[2]
        framekey_coords[MMMetadata._CHANNEL] = framekey_nums[1]
        framekey_coords[MMMetadata._TIME] = framekey_nums[0]
        return framekey_coords


class LSPycroMetadata(object):
    """
    Class to hold metadata from LSPycroApp. 

    ## Constructor Parameters:

    path: str
        Can be path of tif file, directory of tif file, ls notes file,
        or directory of notes file. If LS Pycro metadata file is not found
        in directory, will recursively search for it.
    """
    #Name of acquisition folder. 
    ACQUISITION = "Acquisition"
    FISH = "Fish"
    REGION = "Region"

    def __init__(self, path: pathlib.Path):
        self.config = ConfigParser()
        self._init_config(path)

    def _init_config(self, path: pathlib.Path):
        path = pathlib.Path(path)
        if path.is_file() and is_ls_pycro_notes(path):
            self.config.read(file)
        elif self.ACQUISITION in path:
            cur_directory = path
            while self.ACQUISITION not in cur_directory.name:
                cur_directory = cur_directory.parent
            file_generator = pathlib.Path(cur_directory)
            file_list = [str(file) for file in file_generator]
            for file in file_list:
                if is_ls_pycro_notes(file):
                    self.config.read(file)
                    break
            else:
                raise FileNotFoundError("LSPycroMetadata file not found.")
        else:
            raise FileNotFoundError("LSPycroMetadata file not found. Not ls pycro acquisition.")
    
    def get_section_dict(self, section: str) -> dict:
        section_dict = {}
        for item in self.config.items(section):
            section_dict[item[0]] = literal_eval(item[1])
        return section_dict
    
    def get_region_dict(self, fish_num: int, region_num: int) -> dict:
        section = self._get_region_section(fish_num, region_num)
        return self.get_section_dict(section)
    
    def get_num_fish(self) -> int:
        num_fish = 0
        for section in self.config.sections():
            if self.FISH in section and self.REGION in section:
                num_fish += 1
        return num_fish
    
    def get_num_regions(self, fish_num: int) -> int:
        region_num = 1
        section = self._get_region_section(fish_num, region_num)
        while self.config.has_section(section):
            region_num += 1
            section = self._get_region_section(fish_num, region_num)
        return region_num - 1

    def _get_region_section(self, fish_num: int, region_num: int) -> str:
        return f"{self.FISH} {fish_num} {self.REGION} {region_num}"
    