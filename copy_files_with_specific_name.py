import os
import shutil


def copy_files(source, target, filename_substring_include, pathname_substring_include):
    
    for root, dirs, files in os.walk(source):
        for file in files:
            if filename_substring_include == "":
                string_comparison = pathname_substring_include.casefold() in root.casefold()
            if pathname_substring_include == "":
                string_comparison = filename_substring_include.casefold() in file.casefold()
            if (filename_substring_include != "") and (pathname_substring_include != ""):
                string_comparison = (filename_substring_include.casefold() in file.casefold()) and (pathname_substring_include.casefold() in root.casefold())
                # print(file, root, string_comparison)
                
            if string_comparison:
                # Construct full file path
                source_file = os.path.join(root, file)

                # Construct the target directory path
                relative_path = os.path.relpath(root, source)
                target_dir = os.path.join(target, relative_path)

                # Create the target directory if it doesn't exist
                os.makedirs(target_dir, exist_ok=True)

                # Construct the target file path
                target_file = os.path.join(target_dir, file)

                # Copy the file
                shutil.copy2(source_file, target_file)
                print(f"Copied {source_file} to {target_file}")


# Ask user for source and target directories
source_directory = input("Enter the source directory: ")
target_directory = input("Enter the target directory: ")
file_substring_include = input(
    "Enter the substring of filenames to INCLUDE for copying (can have extensions): "
)

pathname_substring_include = input(
    "Enter the substring of pathname to INCLUDE for copying [default='']: "
) or ""

copy_files(source_directory, target_directory, filename_substring_include=file_substring_include, pathname_substring_include=pathname_substring_include)

# add successful message
print(f"Done! Copied files are in: {target_directory}")
# wait for user to close the window
input("Press Enter to close the program...")
exit()
