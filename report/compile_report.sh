#!/bin/bash

# Compile the LaTeX report for the Conference Management System

echo "Compiling Conference Management System Report..."

# First pdflatex run to generate initial files
echo "Running first pdflatex pass..."
pdflatex -synctex=1 -interaction=nonstopmode -file-line-error main.tex
echo "Done with first pass."

# Second pdflatex run to resolve cross-references and table of contents
echo "Running second pdflatex pass to resolve references..."
pdflatex -synctex=1 -interaction=nonstopmode -file-line-error main.tex
echo "Done with second pass."

# Check if compilation was successful
if [ -f "main.pdf" ]; then
    echo "Compilation completed successfully! PDF available at: main.pdf"
else
    echo "Error: PDF generation failed. Check the log file for errors."
    exit 1
fi 