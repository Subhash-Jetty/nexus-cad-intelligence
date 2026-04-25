def validate_design(geom_data, material_tier="Medium (Standard Use)"):
    issues = []
    score = 100

    if not geom_data.get("is_watertight"):
        issues.append({
            "rule": "Manifold Geometry",
            "raw_value": "Non-watertight mesh",
            "severity": "Critical"
        })
        score -= 40

    min_t = geom_data.get("min_thickness_mm", 0)
    
    # Updated: Simple Low/Medium/High Tiers
    thresholds = {
        "Low (e.g., Plastic/Prototyping)": 2.0,
        "Medium (e.g., Aluminum/Standard)": 1.0,
        "High (e.g., Steel/Heavy Duty)": 0.5
    }
    target_t = thresholds.get(material_tier, 1.0)

    if min_t < target_t:
        issues.append({
            "rule": f"Minimum Wall Thickness for {material_tier.split(' ')[0]} tier",
            "raw_value": f"{min_t} mm (Target: {target_t} mm)",
            "severity": "High"
        })
        score -= 25

    faces = geom_data.get("faces", 0)
    if faces > 500000:
        issues.append({
            "rule": "Over-tessellation",
            "raw_value": f"{faces} faces",
            "severity": "Low"
        })
        score -= 10

    return {
        "score": max(0, score),
        "issues": issues,
        "is_passed": score >= 80,
        "material": material_tier
    }