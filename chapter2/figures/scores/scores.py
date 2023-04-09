"""Make figure of disorder score evolution."""

import os
import re
from textwrap import shorten

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import skbio
from src2.draw import plot_msa_data
from src2.phylo import get_brownian_weights
from src2.utils import read_fasta


def load_scores(path):
    with open(path) as file:
        scores = []
        for line in file:
            if not line.startswith('#'):
                score = line.split()[3]
                scores.append(score)
    return scores


ppid_regex = r'ppid=([A-Za-z0-9_.]+)'
spid_regex = r'spid=([a-z]+)'
min_length = 30

panel_records = [('0F47', 0, None),
                 ('07E3', 350, 650),
                 ('146F', 125, 525),
                 ('1432', 9, 325)]
plt.rcParams['xtick.labelsize'] = 8
plt.rcParams['ytick.labelsize'] = 8
plt.rcParams['axes.labelsize'] = 8
plt.rcParams['legend.fontsize'] = 8
width_ratios = (0.3, 0.3, 0.4)
rect_B = (0.375, 0.06, 0.5475, 0.92)
rect_CD = (0.25, 0.18, 0.7, 0.7)
rect_E = (0.5, 0.325, 0.475, 0.65)
plot_msa_kwargs = {'hspace': 0.01, 'left': 0.15, 'right': 0.85, 'top': 0.95, 'bottom': 0.025, 'anchor': (0, 0.5),
                   'data_min': -0.05, 'data_max': 1.05,
                   'tree_position': 0, 'tree_width': 0.15,
                   'msa_legend': True, 'legend_kwargs': {'bbox_to_anchor': (0.85, 0.5), 'loc': 'center left', 'fontsize': 8,
                                                         'handletextpad': 0.5, 'markerscale': 1.5, 'handlelength': 1}}

tree_template = skbio.read('../../IDR_evolution/data/trees/consensus_LG/100R_NI.nwk', 'newick', skbio.TreeNode)
tip_order = {tip.name: i for i, tip in enumerate(tree_template.tips())}

if not os.path.exists('out/'):
    os.mkdir('out/')

fig = plt.figure(figsize=(7.5, 8.5))
gs = plt.GridSpec(4, 3, width_ratios=width_ratios)
dp = fig.dpi_scale_trans.transform((0.0625, -0.0625))

for panel_OGid, panel_start, panel_stop in panel_records:
    # --- PANEL A ---
    # Load MSA
    msa = []
    for header, seq in read_fasta(f'../../IDR_evolution/data/alignments/fastas/{panel_OGid}.afa'):
        ppid = re.search(ppid_regex, header).group(1)
        spid = re.search(spid_regex, header).group(1)
        msa.append({'ppid': ppid, 'spid': spid, 'seq': seq})
    msa = sorted(msa, key=lambda x: tip_order[x['spid']])

    # Get missing segments
    ppid2missing = {}
    with open(f'../../IDR_evolution/data/alignments/missing/{panel_OGid}.tsv') as file:
        field_names = file.readline().rstrip('\n').split('\t')
        for line in file:
            fields = {key: value for key, value in zip(field_names, line.rstrip('\n').split('\t'))}
            missing = []
            for s in fields['slices'].split(','):
                if s:
                    start, stop = s.split('-')
                    missing.append((int(start), int(stop)))
            ppid2missing[fields['ppid']] = missing

    # Align scores and interpolate between gaps that are not missing segments
    aligned_scores = np.full((len(msa), len(msa[0]['seq'])), np.nan)
    for i, record in enumerate(msa):
        ppid, seq = record['ppid'], record['seq']
        scores = load_scores(f'../../IDR_evolution/analysis/IDRpred/get_scores/out/{panel_OGid}/{ppid}.diso_noprof')  # Remove anything after trailing .
        idx = 0
        for j, sym in enumerate(seq):
            if sym not in ['-', '.']:
                aligned_scores[i, j] = scores[idx]
                idx += 1

        nan_idx = np.isnan(aligned_scores[i])
        range_scores = np.arange(len(msa[0]['seq']))
        interp_scores = np.interp(range_scores[nan_idx], range_scores[~nan_idx], aligned_scores[i, ~nan_idx],
                                  left=np.nan, right=np.nan)
        aligned_scores[i, nan_idx] = interp_scores

        for start, stop in ppid2missing[ppid]:
            aligned_scores[i, start:stop] = np.nan
    aligned_scores = np.ma.masked_invalid(aligned_scores)

    # Get Brownian weights and calculate root score
    spids = [record['spid'] for record in msa]
    tree = tree_template.shear(spids)
    for node in tree.postorder():  # Ensure tree is ordered as in original
        if node.is_tip():
            node.value = tip_order[node.name]
        else:
            node.children = sorted(node.children, key=lambda x: x.value)
            node.value = sum([child.value for child in node.children])

    tips, weights = get_brownian_weights(tree)
    weight_dict = {tip.name: weight for tip, weight in zip(tips, weights)}
    weight_array = np.zeros((len(msa), 1))
    for i, record in enumerate(msa):
        weight_array[i] = weight_dict[record['spid']]

    weight_sum = (weight_array * ~aligned_scores.mask).sum(axis=0)
    root_scores = (weight_array * aligned_scores).sum(axis=0) / weight_sum
    rate_scores = (weight_array * (aligned_scores - root_scores) ** 2).sum(axis=0) / weight_sum
    upper = root_scores + rate_scores ** 0.5
    lower = root_scores - rate_scores ** 0.5

    # Format tree colors
    # Tip values are assigned by using a cumulative sum of Brownian weights in tip order to span the interval [0, 1]
    # Tip colors are assigned by using a colormap to map this value to a color
    # The values of internal nodes are calculated using a weighted average of the tip values
    # These values are then converted to colors with the colormap; this ensures all colors are "in" the colormap
    cmap = plt.colormaps['magma']
    get_color = lambda x: cmap(0.8 * x + 0.1)  # Shift range to [0.1, 0.9]
    weight_dict = {tip.name: weight for tip, weight in zip(tips, weights)}
    value_dict = {tip.name: i / len(tips) for i, tip in enumerate(tips)}

    node2color, node2names = {}, {}
    for node in tree.postorder():
        if node.is_tip():
            node2color[node] = get_color(value_dict[node.name])
            node2names[node] = [node.name]
        else:
            names = [name for child in node.children for name in node2names[child]]
            ws = [weight_dict[name] for name in names]
            vs = [value_dict[name] for name in names]
            value = sum([w * v for w, v in zip(ws, vs)]) / sum(ws)
            node2color[node] = get_color(value)
            node2names[node] = names

    # Plot all score traces
    subfig = fig.add_subfigure(gs[:2, :2])
    plot_msa_data([record['seq'][panel_start:panel_stop] for record in msa], aligned_scores[:, panel_start:panel_stop],
                  fig=subfig, figsize=(4.5, 4.325),
                  x_start=panel_start, data_linewidths=1, data_colors=[node2color[tip] for tip in tree.tips()],
                  tree=tree, tree_kwargs={'linewidth': 0.75, 'linecolor': node2color,
                                          'tip_labels': False, 'xmin_pad': 0.025, 'xmax_pad': 0.025},
                  **plot_msa_kwargs)
    axs = [ax for i, ax in enumerate(fig.axes) if i % 2 == 1]
    for ax in axs:
        ax.set_ylabel('Score')
    x, y = subfig.transSubfigure.inverted().transform(subfig.transSubfigure.transform((0, 1)) + dp)
    subfig.suptitle('A', x=x, y=y, ha='left', fontweight='bold')

    # --- PANEL B ---
    # Load regions as segments
    rows = []
    with open(f'../../IDR_evolution/analysis/IDRpred/region_filter/out/regions_{min_length}.tsv') as file:
        field_names = file.readline().rstrip('\n').split('\t')
        for line in file:
            fields = {key: value for key, value in zip(field_names, line.rstrip('\n').split('\t'))}
            OGid, start, stop, disorder = fields['OGid'], int(fields['start']), int(fields['stop']), fields['disorder'] == 'True'
            for ppid in fields['ppids'].split(','):
                rows.append({'OGid': OGid, 'start': start, 'stop': stop, 'disorder': disorder, 'ppid': ppid})
    all_segments = pd.DataFrame(rows)
    all_regions = all_segments.drop('ppid', axis=1).drop_duplicates()

    feature_roots = pd.read_table(f'../../IDR_evolution/analysis/brownian/get_contrasts/out/features/roots_{min_length}.tsv', header=[0, 1])
    feature_labels = [feature_label for feature_label, group_label in feature_roots.columns if group_label != 'ids_group']
    nonmotif_labels = [feature_label for feature_label, group_label in feature_roots.columns if group_label not in ['ids_group', 'motifs_group']]

    feature_contrasts = pd.read_table(f'../../IDR_evolution/analysis/brownian/get_contrasts/out/features/contrasts_{min_length}.tsv', skiprows=[1])  # Skip group row
    feature_contrasts = all_regions.merge(feature_contrasts, how='left', on=['OGid', 'start', 'stop'])
    feature_contrasts = feature_contrasts.set_index(['OGid', 'start', 'stop', 'disorder', 'contrast_id'])

    score_contrasts = pd.read_table(f'../../IDR_evolution/analysis/brownian/get_contrasts/out/scores/contrasts_{min_length}.tsv')
    score_contrasts = all_regions.merge(score_contrasts, how='left', on=['OGid', 'start', 'stop'])
    score_contrasts = score_contrasts.set_index(['OGid', 'start', 'stop', 'disorder', 'contrast_id'])

    ys = np.arange(len(feature_labels))
    xs = np.corrcoef(score_contrasts['score_fraction'], feature_contrasts, rowvar=False)[1:, 0]  # Remove score_fraction self correlation
    ps = pd.read_table(f'../../IDR_evolution/analysis/brownian/contrast_stats/out/regions_{min_length}/scores/pvalues.tsv')['pvalue']

    subfig = fig.add_subfigure(gs[:3, 2])
    ax = subfig.add_axes(rect_B)
    ax.invert_yaxis()
    ax.set_ymargin(0.005)
    ax.barh(ys, xs)
    ax.set_yticks(ys, feature_labels, fontsize=5.5)
    ax.set_xlabel('Correlation')
    ax.set_ylabel('Feature')
    alpha = 0.001
    offset = (xs.max() - xs.min()) / 200
    for y, x, p in zip(ys, xs, ps):
        if p <= alpha:
            sign = 1 if x >= 0 else -1
            rotation = -90 if x >= 0 else 90
            ax.text(x + sign * offset, y, '*', fontsize=6, va='center', ha='center', rotation=rotation)
    x, y = subfig.transSubfigure.inverted().transform(subfig.transSubfigure.transform((0, 1)) + dp)
    subfig.suptitle('B', x=x, y=y, ha='left', fontweight='bold')

    # --- PANEL C AND D ---
    subfig = fig.add_subfigure(gs[2, 0])
    ax = subfig.add_axes(rect_CD)
    hb = ax.hexbin(score_contrasts['score_fraction'], feature_contrasts['isopoint'],
                   gridsize=35, mincnt=1, linewidth=0, bins='log')
    ax.set_xlabel('Score contrasts')
    ax.set_ylabel('isopoint contrasts')
    subfig.colorbar(hb)
    x, y = subfig.transSubfigure.inverted().transform(subfig.transSubfigure.transform((0, 1)) + dp)
    subfig.suptitle('C', x=x, y=y, ha='left', fontweight='bold')

    subfig = fig.add_subfigure(gs[2, 1])
    ax = subfig.add_axes(rect_CD)
    hb = ax.hexbin(score_contrasts['score_fraction'], feature_contrasts['hydropathy'],
                   gridsize=35, mincnt=1, linewidth=0, bins='log')
    ax.set_xlabel('Score contrasts')
    ax.set_ylabel('hydropathy contrasts')
    subfig.colorbar(hb)
    x, y = subfig.transSubfigure.inverted().transform(subfig.transSubfigure.transform((0, 1)) + dp)
    subfig.suptitle('D', x=x, y=y, ha='left', fontweight='bold')

    # --- PANEL E ---
    pvalues = pd.read_table('../../IDR_evolution/analysis/GOpred/score_enrich/out/pvalues_regions.tsv')

    subfig = fig.add_subfigure(gs[3, :])
    ax = subfig.add_axes(rect_E)
    bars = [('P', 'Process'), ('F', 'Function'), ('C', 'Component')]
    y0, labels = 0, []
    for aspect, aspect_label in bars:
        data = pvalues[(pvalues['aspect'] == aspect) & (pvalues['pvalue'] <= 0.001)]
        xs = -np.log10(data['pvalue'])
        ys = np.arange(y0, y0 + 2 * len(xs), 2)
        for GOid, name in zip(data['GOid'], data['name']):
            label = f'{shorten(name, width=80, placeholder=" ...")} ({GOid})'
            labels.append(label)
        y0 += 2 * len(xs)
        ax.barh(ys, xs, label=aspect_label, height=1.25)
    ax.invert_yaxis()
    ax.set_ymargin(0.01)
    ax.set_yticks(np.arange(0, 2 * len(labels), 2), labels, fontsize=5.5)
    ax.set_xlabel('$\mathregular{-log_{10}}$(p-value)')
    ax.set_ylabel('Term')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.275), ncol=len(bars))
    x, y = subfig.transSubfigure.inverted().transform(subfig.transSubfigure.transform((0, 1)) + dp)
    subfig.suptitle('E', x=x, y=y, ha='left', fontweight='bold')

    fig.savefig(f'out/scores_{panel_OGid}.png', dpi=400)
    fig.savefig(f'out/scores_{panel_OGid}.tiff', dpi=400)
    plt.close()