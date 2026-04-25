import trimesh

# Create a thin plate (50x50x1.5mm)
mesh = trimesh.creation.box(extents=[50, 50, 1.5])

# Export as a Binary STL
mesh.export('test_plate.stl', file_type='stl')

print("Success: 'test_plate.stl' has been created in your folder!")