# Commands to create the build

## Creates the spec file
```
pyinstaller --name EasyCV --onefile --add-data "templates;templates" --add-data "static;static" main.py
```

## Creates the executable
```
pyinstaller EasyCV.spec
```