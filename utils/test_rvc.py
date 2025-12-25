import rvc_python
print("RVC Library imported successfully")
try:
    from rvc_python.infer import RVCInference
    print("RVCInference class imported successfully")
except ImportError as e:
    print(f"Failed to import RVCInference: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
