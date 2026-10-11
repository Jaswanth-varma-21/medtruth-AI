"""Short made-up chest X-ray reports for demos and tests (not real patient data)."""

SAMPLES = [
    {
        "id": "normal",
        "title": "Normal chest X-ray",
        "text": (
            "FINDINGS:\nThe lungs are clear. The heart size is normal. "
            "No pleural effusion or pneumothorax. The mediastinal contours are unremarkable.\n"
            "IMPRESSION: No acute cardiopulmonary abnormality."
        ),
    },
    {
        "id": "pneumonia",
        "title": "Possible pneumonia with effusion",
        "text": (
            "FINDINGS:\nThere is a patchy airspace opacity in the right lower lobe, which may represent pneumonia. "
            "There is blunting of the right costophrenic angle suggesting a small pleural effusion. "
            "The cardiac silhouette is enlarged. No pneumothorax is seen.\n"
            "IMPRESSION: Right lower lobe opacity, possibly pneumonia, with small right pleural effusion. Cardiomegaly."
        ),
    },
    {
        "id": "pneumothorax",
        "title": "Small pneumothorax",
        "text": (
            "FINDINGS:\nNo focal consolidation. No pleural effusion. A small right apical pneumothorax is present. "
            "Heart size is normal. Pacemaker in place.\n"
            "IMPRESSION: Small right pneumothorax."
        ),
    },
]
