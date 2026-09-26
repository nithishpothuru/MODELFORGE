from pathlib import Path

from app.services.storage_service import upload_model


# Test model file
model_file = Path("../modelforge_test_model.pkl")

# Read model as binary data
with open(model_file, "rb") as file:
    model_data = file.read()


# Cloud storage path
storage_path = "test/model.pkl"


# Upload to Supabase
response = upload_model(model_data, storage_path)

print("Model uploaded successfully!")
print("Storage path:", storage_path)
print("Response:", response)