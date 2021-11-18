#!/usr/bin/env python3

import os
import shutil
import tempfile
import subprocess
import urllib.parse
from datetime import datetime

import click
import ruamel.yaml as yaml
import requests
import jinja2


def apply_to_leaves(nested, func):
    stack = [nested]

    def isscalar(v):
        return not hasattr(v, "__iter__") or isinstance(v, str)

    while stack:
        item = stack.pop()

        if isinstance(item, list):
            stack.extend(item)

        elif isinstance(item, dict):
            static_items = list(item.items())
            for key, val in static_items:
                if isscalar(val):
                    item[key] = func(key, val)
                else:
                    stack.append(val)

    return nested


def parse_config(infile):
    with open(infile, "r") as f:
        config = yaml.safe_load(f)

    def convert_datetime(key, val):
        if key not in {"start", "end", "date"} or val is None:
            return val

        return datetime.strptime(val, "%d-%m-%Y")

    config = apply_to_leaves(config, convert_datetime)
    return config


def generate_latex(config, template_file, outdir, bibfile=None):
    latex_jinja_env = jinja2.Environment(
        block_start_string='\\BLOCK{',
        block_end_string='}',
        variable_start_string='\\VAR{',
        variable_end_string='}',
        comment_start_string='\\#{',
        comment_end_string='}',
        line_statement_prefix='%%',
        line_comment_prefix='%#',
        trim_blocks=True,
        autoescape=False,
        loader=jinja2.FileSystemLoader(os.path.dirname(template_file))
    )

    template = latex_jinja_env.get_template(os.path.basename(template_file))
    outstr = template.render(**config)
    outfile = os.path.join(outdir, "cv.tex")

    with open(outfile, "w") as f:
        f.write(outstr)

    return outfile


def compile_latex(infile, outdir, bibfile=None):
    outfile = os.path.join(outdir, "cv.pdf")

    subprocess.run([
        "xelatex",
        f"-output-directory={outdir}",
        "-jobname=cv",
        "-interaction=nonstopmode",
        infile,
    ], check=True)

    if bibfile is not None:
        subprocess.run([
            "biber",
            "cv.bcf"
        ], check=True)

        subprocess.run([
            "xelatex",
            f"-output-directory={outdir}",
            "-jobname=cv",
            "-interaction=nonstopmode",
            infile,
        ], check=True)

    return outfile


def generate_bibliography(config, outdir):
    if not config.get("publications"):
        return None

    outstr = []

    for pub in config["publications"]:
        if "doi" in pub:
            pubstr = doi_to_bibtex(pub["doi"])
        elif "bibtex" in pub:
            pubstr = pub["bibtex"]
        else:
            print("Warning: encountered publication without DOI or bibtex")
            continue

        outstr.append(pubstr)

    outstr = "\n".join(outstr)
    outfile = os.path.join(outdir, "publications.bib")

    with open(outfile, "w") as f:
        f.write(outstr)

    return outfile


def doi_to_bibtex(doi):
    BASE_URL = "http://dx.doi.org/"

    url = urllib.parse.urljoin(BASE_URL, doi)
    headers = {"accept": "application/x-bibtex"}

    with requests.get(url, headers=headers) as res:
        res.raise_for_status()
        return res.text


@click.command()
@click.argument("CONFIGFILE", type=click.Path(exists=True, resolve_path=True))
@click.option("-t", "--template", type=click.Path(exists=True, resolve_path=True), required=True)
@click.option("-o", "--outfile", type=click.Path(writable=True, resolve_path=True), required=False)
@click.option("--keep-tempfiles", is_flag=True)
def main(configfile, template, outfile, keep_tempfiles):
    if outfile is None:
        outfile = f"{os.path.splitext(configfile)[0]}.pdf"

    tmpdir = tempfile.mkdtemp()
    os.chdir(tmpdir)

    try:
        config = parse_config(configfile)
        bibfile = generate_bibliography(config, tmpdir)
        texfile = generate_latex(config, template, tmpdir, bibfile=bibfile)
        out = compile_latex(texfile, tmpdir, bibfile=bibfile)
        shutil.copy(out, outfile)
    finally:
        if not keep_tempfiles:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
