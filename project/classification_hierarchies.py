label_hierarchy = [
    {'is_group':True,
     'name':"Animals",
     'elements':{"dog":"Dog","cat":"Cat"}},
    {'is_group':False,
     'name':"",
     'elements':{"per":"Person"}}]
labels_dict = {}
for k in label_hierarchy:
    for kk in k['elements']:
        labels_dict[kk] = k['elements'][kk]
