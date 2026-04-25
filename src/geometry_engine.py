import trimesh
import numpy as np

def analyze_stl(file_object):
    """Parses an STL file and returns key geometric properties."""
    try:
        # Load mesh directly, but tell trimesh NOT to process/clean it
        # This bypasses the strict "coplanar" math errors
        mesh = trimesh.load(file_object, file_type='stl', process=False)
        
        # Extract dimensions
        extents = mesh.bounding_box_oriented.extents
        min_thickness = np.min(extents)
        
        return {
            "is_watertight": mesh.is_watertight,
            "min_thickness_mm": round(min_thickness, 2),
            "dimensions_mm": [round(x, 2) for x in extents],
            "volume_mm3": round(mesh.volume, 2) if mesh.is_watertight else 0,
            "faces": len(mesh.faces),
            "status": "success"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}