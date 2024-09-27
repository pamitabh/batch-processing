import os
import shutil


def copy_mask_files(source, target, file_substring):
    for root, dirs, files in os.walk(source):
        for file in files:
            if file_substring in file.casefold():
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
file_substring = input(
    "Enter the substring to filter filenames for copying (can have extensions): "
)

copy_mask_files(source_directory, target_directory, file_substring=file_substring)

# add successful message
print(f"Done! Copied files are in: {target_directory}")
# wait for user to close the window
input("Press Enter to close the program...")
exit()
