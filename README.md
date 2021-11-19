# CV

My personal [CV](generated/cv.pdf?raw=true) and [résumé](generated/resume.pdf?raw=true), auto-generated via GitHub Actions.

## Requirements

- Python >= 3.6
- XeLaTeX
- biblatex
- `fontawesome5` LaTeX package
- Source Sans Pro fonts

## Usage

Edit `content.yaml` and / or `config-cv.yaml`, then run

```bash
$ python generate.py config-cv.yaml
```

or push your changes and let GitHub Actions generate the PDFs.
