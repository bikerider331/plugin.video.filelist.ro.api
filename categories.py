import json

class Categories:
    def __init__(self, addonRootPath):
        with open(addonRootPath + "/resources/categories.json") as json_file:
            self.categories = json.load(json_file)
            self.categoriesById = {}
            self.categoriesByName = {}
            for c in self.categories:
                id = c['id']
                name = c['name']
                self.categoriesById[id] = c
                self.categoriesByName[name] = c

    def get_category_by_id(self, id):
        return self.categoriesById[id]

    def get_category_by_name(self, name):
        return self.categoriesByName[name]

    def get_categories(self):
        return self.categories    
