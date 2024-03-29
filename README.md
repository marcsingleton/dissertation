# Dissertation

This is the repo for my dissertation manuscript. It contains the formatting and text of the manuscript in the form of LaTeX files as well as the Python code used to generate the figures. To keep the presentation of data separate from their generation, this project was spun off from two other repos, [Orthology Inference](https://github.com/marcsingleton/orthology_inference2023) and [IDR Evolution](https://github.com/marcsingleton/IDR_evolution2023). Thus, compiling the manuscript depends on resources available in these repos, and accordingly the figure generation code expects links to certain portions of them, which is described in more detail in the Project Organization section.

Excluding a few subsequent bookkeeping commits, this repo was largely "frozen" in May 2023 with the submission of my dissertation, but the Orthology Inference and IDR Evolution repos have since undergone additional development to prepare them for publication as standalone articles. (You can view the status of these efforts on their individual project repos.) The commits corresponding to archived version of my dissertation are tagged as "ProQuest," so the project can be easily restored to its state at the time of its submission.

## Project Organization

The project is organized into four chapters, each of which corresponds to a directory in the project root. These chapter directories in turn contain LaTeX files with the text of those chapters. Figures are generated by Python scripts which generally are stored in their own subdirectories under the `figures/` directory of each chapter. To access utility functions and data from the main repos, these scripts expect links to local copies of the main repos in their corresponding chapter directories as well as to the main repos' `src/` directories in the root of this repo. (The directory of this repo should also be in your environment's PYTHONPATH to allow Python to import these `src/` "directories" as modules in the figure generation scripts.) The exact structure and naming conventions are easier shown than described, so below I've included a partial directory tree of the project to illustrate.

```
dissertation/
	├── chapter0/
	├── chapter1/
	│	├── orthology_inference/   (link to /local/path/to/orthology_inference/)
	│	└── ...
	├── chapter2/
	│	├── IDR_evolution/         (link to /local/path/to/IDR_evolution/)
	│	└── ...
	├── chapter3/
	├── src1/   (link to /local/path/to/orthology_inference/src/)
	├── src2/   (link to /local/path/to/IDR_evolution/src/)
	├── src3/   (link to /local/path/to/homomorph/src/tutorials/)
	└── ...     (other files omitted for brevity)
```
