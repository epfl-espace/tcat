Welcome to Sphinx doc 101:

1. comment your code following Sphinx template:
    - comments in the code must follow sphinx template: - for more info on comments formatting: https://www.sphinx-doc.org/en/master/tutorial/describing-code.html#documenting-python-objects
    - Visual Studio Code have powerfull tool to help formating comments:
        - download autoDocstring extension for VSCode
        - in VSCode settings.json (use ctr+p tofind file), add: "autoDocstring.docstringFormat": "sphinx",
        - in your code, right under a function definition, right-click --> generate_docstring
    
2. install required pyhon package:
    - conda install -c conda-forge sphinx_rtd_theme (for nice html template)

3. build and run your doc:
    - using prompt (i.e. Anaconda prompt), move to ./Doc repository
    - enter: make html
    - open with Chrome: ./Doc/_buid/html/index.html

4. to add a module to the doc:
    - open: .Doc/documentation.rst
    - follow logic of the template to add your module

5. usefull links:
    - to perform hyperlinks: https://kevin.burke.dev/kevin/sphinx-interlinks/
