import inspect
from rvc_python.infer import RVCInference

print("load_model:", inspect.signature(RVCInference.load_model))
print("set_params:", inspect.signature(RVCInference.set_params) if hasattr(RVCInference, 'set_params') else "No set_params")
