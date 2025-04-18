# Commands to create the build

## Creates the spec file
```
pyinstaller --name EasyCV --onefile --add-data "templates;templates" --add-data "static;static" --add-data "database.db;." main.py
```

## Creates the executable
```
pyinstaller EasyCV.spec
```