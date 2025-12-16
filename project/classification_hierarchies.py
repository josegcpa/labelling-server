import yaml

def get_label_hierarchy_dict(config_path: str):
    with open(config_path) as o:
        label_hierarchy = yaml.safe_load(o)["classes"]
    labels_dict = {}
    for k in label_hierarchy:
        for kk in k['elements']:
            labels_dict[kk] = k['elements'][kk]
    return label_hierarchy, labels_dict

label_hierarchy, labels_dict = get_label_hierarchy_dict("config.yaml")