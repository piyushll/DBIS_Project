# Conference Management System Report

This directory contains the LaTeX source files for the Conference Management System project report.

## Compiling with LaTeX Workshop in VS Code

### Prerequisites

1. Install VS Code: [https://code.visualstudio.com/](https://code.visualstudio.com/)
2. Install the LaTeX Workshop extension:
   - Open VS Code
   - Go to Extensions (Ctrl+Shift+X)
   - Search for "LaTeX Workshop"
   - Install the extension by James Yu

3. Ensure you have a LaTeX distribution installed on your system:
   - **Linux**: TexLive (`sudo apt-get install texlive-full`)
   - **macOS**: MacTeX
   - **Windows**: MiKTeX or TexLive

### Compiling the Report

1. Open the project folder in VS Code
2. The LaTeX Workshop extension is already configured through the `.vscode/settings.json` file
3. Open `report/main.tex` in VS Code
4. To compile the document:
   - Use the LaTeX Workshop sidebar (TeX icon on the left sidebar)
   - Click on "Build LaTeX project" or use the shortcut (Ctrl+Alt+B)
   - The default recipe "pdflatex × 2" will be used automatically
   - Alternatively, use the keyboard shortcut Ctrl+S to save, which will trigger auto-build

5. To view the PDF:
   - Click on "View LaTeX PDF file" in the LaTeX Workshop sidebar
   - Or use the shortcut (Ctrl+Alt+V)

### Project Structure

- `main.tex` - Main document file that includes all sections
- `data_loading.tex` - Section on data loading process
- `backend_implementation.tex` - Backend implementation details
- `frontend_implementation.tex` - Frontend implementation details
- `table_viewer_feature.tex` - Specialized section on the table viewer feature
- `database_appendix.tex` - Appendix with database structure details

### Troubleshooting

If you encounter compilation issues:

1. Check the LaTeX Workshop output panel for error messages
2. Ensure all required LaTeX packages are installed
3. Try running the "Clean up auxiliary files" command in the LaTeX Workshop sidebar
4. Restart VS Code if the extension is not responding

For more detailed troubleshooting, refer to the [LaTeX Workshop documentation](https://github.com/James-Yu/LaTeX-Workshop/wiki).

### Manual Compilation

If you prefer to compile manually or are having issues with LaTeX Workshop, you can:

1. Use the provided compile script:
```bash
cd report
./compile_report.sh
```

2. Or run pdflatex manually:
```bash
cd report
pdflatex -synctex=1 -interaction=nonstopmode -file-line-error main.tex
pdflatex -synctex=1 -interaction=nonstopmode -file-line-error main.tex
```

Run pdflatex twice to ensure proper cross-references and table of contents generation.

### Notes

- The configuration uses `pdflatex` run twice for proper cross-references
- The PDF will be generated in the same directory as the main.tex file
- No bibliography is used in this project, so BibTeX is not required

## Files Structure

- `main.tex` - The main LaTeX document that includes all sections
- `data_loading.tex` - Section about database schema and data loading
- `backend_implementation.tex` - Section about server-side implementation
- `frontend_implementation.tex` - Section about frontend implementation
- `table_viewer_feature.tex` - Detailed section about the table viewer feature

## How to Compile

### Using pdflatex (command line)

1. Make sure you have a LaTeX distribution installed (TeX Live, MiKTeX, or MacTeX)
2. Navigate to the report directory
3. Run the following commands:

```bash
pdflatex main.tex
pdflatex main.tex  # Run twice for proper references and table of contents
```

The output will be a file named `main.pdf`.

### Using an IDE/Editor (TeXStudio, Overleaf, etc.)

1. Open the `main.tex` file in your LaTeX editor
2. Use the build/compile button to generate the PDF
3. Make sure to compile twice for proper references and table of contents

## Required LaTeX Packages

The report uses the following LaTeX packages, which should be included in most standard LaTeX distributions:

- inputenc
- fontenc
- lmodern
- hyperref
- graphicx
- amsmath
- amssymb
- listings
- xcolor
- booktabs
- geometry
- fancyhdr
- titlesec
- enumitem

## Troubleshooting

If you encounter compilation errors:

1. Make sure all .tex files are in the same directory
2. Check that you have all required LaTeX packages installed
3. Look for syntax errors in the LaTeX code
4. Try running with the `--shell-escape` option if using any external tools

For additional help, refer to LaTeX documentation or forums like TeX Stack Exchange. 