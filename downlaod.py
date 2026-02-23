import kagglehub

# Download latest version
path = kagglehub.dataset_download("alinesellwia/food-freshness")

print("Path to dataset files:", path)