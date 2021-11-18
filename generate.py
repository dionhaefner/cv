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

here = os.path.abspath(os.path.dirname(__file__))


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


def parse_config(content_file, config_file):
    with open(content_file, "r") as f:
        contents = yaml.safe_load(f)

    def convert_datetime(key, val):
        if key not in {"start", "end", "date"} or val is None:
            return val

        return datetime.strptime(val, "%d-%m-%Y")

    def convert_newlines(key, val):
        if not isinstance(val, str):
            return val

        return val.replace("\n", "\n\n")

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    template = os.path.join(here, "templates", f"{config['template']}.tex.in")

    for key, vals in config["contents"].items():
        contents[key] = {v: contents[key][v] for v in vals}

    contents = apply_to_leaves(contents, convert_datetime)
    contents = apply_to_leaves(contents, convert_newlines)
    return contents, template


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


def compile_latex(infile, outdir):
    outfile = os.path.join(outdir, "cv.pdf")

    subprocess.run([
        "latexmk",
        "-jobname=cv",
        "-xelatex",
        f"-output-directory={outdir}",
        infile,
    ], check=True)

    return outfile


def generate_bibliography(config, outdir):
    if not config.get("publications"):
        return None

    outstr = []

    for pub in config["publications"].values():
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
@click.option("-c", "--contents", type=click.Path(exists=True, resolve_path=True), default=os.path.join(here, "content.yaml"))
@click.option("-o", "--outfile", type=click.Path(writable=True, resolve_path=True), default=None)
@click.option("--keep-tempfiles", is_flag=True)
def main(configfile, contents, outfile, keep_tempfiles):
    if outfile is None:
        outname, _ = os.path.splitext(os.path.basename(configfile))
        if outname.startswith("config-"):
            outname = outname[7:]

        outfile = os.path.join(here, "generated", f"{outname}.pdf")

    tmpdir = tempfile.mkdtemp()
    os.chdir(tmpdir)

    if keep_tempfiles:
        print(f" > Writing files to {tmpdir}")

    try:
        config, template = parse_config(contents, configfile)
        bibfile = generate_bibliography(config, tmpdir)
        texfile = generate_latex(config, template, tmpdir, bibfile=bibfile)
        out = compile_latex(texfile, tmpdir)
        shutil.copy(out, outfile)
    finally:
        if not keep_tempfiles:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
