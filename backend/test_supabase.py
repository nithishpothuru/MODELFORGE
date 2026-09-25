from app.services.storage_service import supabase, BUCKET_NAME


response = supabase.storage.list_buckets()

print("Supabase connection successful!")
print("Available buckets:")

for bucket in response:
    print("-", bucket.name)