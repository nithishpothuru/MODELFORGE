import zipfile

zip_path = "my_folder.zip"
extract_to = "extracted"

with zipfile.ZipFile(zip_path, "r") as zip_ref:
    zip_ref.extractall(extract_to)

print("Files extracted successfully!")
