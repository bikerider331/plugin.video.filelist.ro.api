import json

class Categories:
    def __init__(self, addonRootPath):
        with open(addonRootPath+"/resources/categories.json") as json_file:
            self.categories = json.load(json_file)
            self.categoriesById = {}
            self.categoriesByName = {}
            for c in self.categories:
                id = c['id']
                name = c['name']
                self.categoriesById[id] = c
                self.categoriesByName[name] = c

    def getCategoryById(self, id):
        return self.categoriesById[id]

    def getCategoryByName(self, name):
        return self.categoriesByName[name]

    def getCategories(self):
        return self.categories    
