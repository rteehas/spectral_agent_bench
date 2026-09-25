#!/usr/bin/env python3
"""Evaluator-only illustrative representation-discovery investigation.

The author knew the virtual-PDF idea. This is an executed scientific candidate,
not evidence of independent invention and not a required solver recipe.
Only numeric spectra and metadata under --inputs are read.
"""
import argparse
import csv
import hashlib
import json
import shutil
import time
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter1d
from sklearn.linear_model import RidgeClassifier

CHEMS = ['Li-La-Zr-O', 'Li-Ti-P-O']
SEED = 261025
THETA = np.linspace(10.02, 79.98, 2001)
R = np.linspace(1, 120, 1191)
WINDOWS = {'pdf_1_5':(1,5), 'pdf_5_40':(5,40), 'pdf_1_40':(1,40), 'pdf_40_120':(40,120.00001)}
METHODS = ['raw_xrd','sqrt_xrd','background_subtracted_xrd','derivative_xrd',*WINDOWS]
DISPLAY = {'raw_xrd':'Raw XRD','sqrt_xrd':'Signed sqrt','background_subtracted_xrd':'Background subtraction','derivative_xrd':'Smoothed derivative',
           'pdf_1_5':'PDF 1–5 Å','pdf_5_40':'PDF 5–40 Å','pdf_1_40':'PDF 1–40 Å','pdf_40_120':'PDF 40–120 Å'}


def write(path, value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def csvwrite(path, rows, fields=None):
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields or list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def load(inputs, chemistry):
    stem=f'{chemistry}_1-Phase'
    rows=json.loads((inputs/f'{stem}.json').read_text())
    with np.load(inputs/f'{stem}.npz',allow_pickle=False) as arrays:
        values=np.array([np.interp(THETA,arrays['theta'],arrays[row['id']]) for row in rows])
    values-=np.percentile(values,10,axis=1,keepdims=True)
    values/=np.maximum(values.max(axis=1,keepdims=True),1e-30)
    return rows,values


def unit(values):
    return values/np.maximum(np.linalg.norm(values,axis=-1,keepdims=True),1e-30)


def split(rows):
    labels=np.array([row['phases'][0] for row in rows])
    roles=np.full(len(rows),'',dtype='U10')
    rng=np.random.default_rng(SEED)
    for label in sorted(set(labels)):
        indexes=np.flatnonzero(labels==label)
        indexes=indexes[rng.permutation(len(indexes))]
        ntrain,nval=int(.6*len(indexes)),max(1,int(.2*len(indexes)))
        roles[indexes[:ntrain]]='train';roles[indexes[ntrain:ntrain+nval]]='validation';roles[indexes[ntrain+nval:]]='test'
    return labels,roles


def make_kernel():
    q=4*np.pi*np.sin(np.deg2rad(THETA/2))/1.5406
    weights=np.empty(len(q));weights[0]=(q[1]-q[0])/2;weights[-1]=(q[-1]-q[-2])/2;weights[1:-1]=(q[2:]-q[:-2])/2
    return 2/np.pi*np.sin(R[:,None]*q[None,:])*(q*weights)[None,:]


KERNEL=make_kernel()
MASKS={name:(R>=bounds[0])&(R<bounds[1]) for name,bounds in WINDOWS.items()}


def features(values):
    transformed=values@KERNEL.T
    return {
        'raw_xrd':values,
        'sqrt_xrd':np.sign(values)*np.sqrt(np.abs(values)),
        'background_subtracted_xrd':values-gaussian_filter1d(values,80,axis=1,mode='reflect'),
        'derivative_xrd':np.gradient(gaussian_filter1d(values,1,axis=1,mode='reflect'),THETA,axis=1),
        **{name:transformed[:,mask] for name,mask in MASKS.items()}
    }


def conditions():
    result=[dict(condition='baseline',artifact='clean',description='Released simulated spectrum, with no newly added artifact.')]
    for amplitude in [.01,.04]:
        for trial in range(3):
            result.append(dict(condition=f'noise_{amplitude}_trial{trial}',artifact='noise',description=f'Independent Gaussian intensity noise with sigma {amplitude} relative to normalized peak height; draw {trial}.'))
    for amplitude in [.05,.25]:
        result.append(dict(condition=f'background_{amplitude}',artifact='background',description=f'Broad Gaussian intensity background with peak {amplitude}, center 35 degrees, standard deviation 12 degrees.'))
    return result


CONDITIONS=conditions()


def perturb(values, condition, seed):
    if condition=='baseline':return values.copy()
    fields=condition.split('_');amplitude=float(fields[1])
    if fields[0]=='noise':return values+np.random.default_rng(seed).normal(0,amplitude,values.shape)
    return values+amplitude*np.exp(-.5*((THETA-35)/12)**2)


def balanced_average(values):
    return float(np.mean([np.mean([values[row['condition']] for row in CONDITIONS if row['artifact']==artifact]) for artifact in ['clean','noise','background']]))


def interval(values, blocks):
    values,blocks=np.asarray(values,float),np.asarray(blocks)
    names=sorted(set(blocks))
    totals=np.array([values[blocks==name].sum() for name in names]);counts=np.array([(blocks==name).sum() for name in names])
    draws=np.random.default_rng(SEED).integers(0,len(names),size=(2000,len(names)))
    distribution=totals[draws].sum(axis=1)/counts[draws].sum(axis=1)
    return dict(estimate=float(values.mean()),blocks=len(names),ci95=list(map(float,np.quantile(distribution,[.025,.975]))))


def weak_pairs(chemistry, values, labels, training):
    classes=sorted(set(labels))
    templates=np.array([values[training&(labels==label)].mean(axis=0) for label in classes])
    cosine=unit(templates)@unit(templates).T
    candidates=[(float(cosine[a,b]),a,b) for a in range(len(classes)) for b in range(a+1,len(classes))]
    selected=sorted(candidates,reverse=True)[:3]
    all_features=features(templates)
    rows=[]
    for similarity,a,b in selected:
        difference=templates[a]-templates[b]
        weak=np.maximum(np.abs(templates[a]),np.abs(templates[b]))<.2
        rows.append(dict(chemistry=chemistry,phase_a=classes[a],phase_b=classes[b],
            raw_cosine=similarity,weak_region_fraction=float(weak.mean()),
            fraction_difference_energy_below_20percent_peak=float(np.sum(difference[weak]**2)/max(1e-30,np.sum(difference**2))),
            **{f'{name}_cosine':float(unit(array[[a]])[0]@unit(array[[b]])[0]) for name,array in all_features.items()}))
    _,a,b=selected[0]
    return rows,(classes[a],classes[b],templates[a],templates[b])


def peak_ablation(chemistry, model, values, labels):
    """Validation-only feature deletion; never reported as held-out predictions."""
    count=max(1,int(.1*values.shape[1]))
    order=np.argsort(np.abs(values),axis=1)
    strong=np.zeros_like(values,dtype=bool);weak=np.zeros_like(values,dtype=bool)
    np.put_along_axis(strong,order[:,-count:],True,axis=1)
    np.put_along_axis(weak,order[:,:count],True,axis=1)
    rng=np.random.default_rng(SEED+41)
    random_masks=[]
    for _ in range(20):
        mask=np.zeros_like(values,dtype=bool)
        for index in range(len(values)):
            mask[index,rng.choice(values.shape[1],count,replace=False)]=True
        random_masks.append(mask)
    def score(array):
        decisions=model.decision_function(unit(array))
        truth_index=np.searchsorted(model.classes_,labels)
        true_scores=decisions[np.arange(len(array)),truth_index]
        alternatives=decisions.copy();alternatives[np.arange(len(array)),truth_index]=-np.inf
        return float(np.mean(model.classes_[decisions.argmax(axis=1)]==labels)),float(np.mean(true_scores-alternatives.max(axis=1)))
    baseline,base_margin=score(values)
    results=[]
    for name,masks in [('strongest_10percent',[strong]),('weakest_10percent',[weak]),('random_10percent',random_masks)]:
        scored=[score(np.where(mask,0,values)) for mask in masks]
        accuracy,margin=np.mean(scored,axis=0)
        results.append(dict(chemistry=chemistry,ablation=name,angle_channels_removed=count,draws=len(masks),
            baseline_accuracy=baseline,ablated_accuracy=float(accuracy),accuracy_change=float(accuracy-baseline),
            mean_true_class_margin=float(margin),margin_change=float(margin-base_margin)))
    return results,dict(strong=strong[:12],weak=weak[:12],random=np.stack(random_masks)[:,:12])


def run(inputs,out):
    started=time.time()
    predictions,splits,metrics,uncertainty,weak_records,localization,confusions=[],[],[],[],[],[],[]
    evidence_ids,evidence_clean,evidence_changed=[],[],[]
    ablations,ablation_ids,ablation_clean,ablation_strong,ablation_weak,ablation_random=[],[],[],[],[],[]
    design=dict(seed=SEED,source='Only released single-phase numeric arrays and labels',
        split='Within-phase seeded shuffle; floor60%train, floor20%validation (at least one), remainingtest',
        discovery_status='Worked illustrative investigation by an author aware of the virtual-PDF idea; not evidence of independent invention.',
        initial_hypotheses=[
            'Strong peaks can dominate vector similarity while useful distinctions occur at weaker intensities; compression may help but can amplify artifacts.',
            'Broad smooth backgrounds corrupt slow reciprocal-space variation; high-pass, derivative, or a physically defined real-space window may separate nuisance from discriminative signal.',
            'An uncorrected Q-weighted sine transform is a physically interpretable alternative whose benefit must be tested against simpler nuisance-removal alternatives.'
        ],
        alternatives=METHODS,
        selection='For each method choose ridgealpha by equal-weight clean/noise/background validation accuracy; then choose the method by the same validation score. Test untouched until all selections are recorded.',
        angular_grid=dict(min_degrees=10.02,max_degrees=79.98,points=2001),
        preprocessing='Linear angular interpolation; tenth-percentile subtraction; peak scaling; feature L2 normalization; retain negative intensities.',
        transform='G(r)=2/pi integral Q I(Q) sin(Qr)dQ; Q=4pi sin(two_theta/2)/1.5406Å; nonuniform-Q trapezoid, r1–120Å in1191points. Uncorrected virtualPDF, not normalized physical pair density.',
        derivative='Gaussian sigma1 angular sample followed by angular finite-difference derivative.',
        background_subtraction='Subtract reflected Gaussian smooth with sigma80 angular samples (~2.8degrees).',
        chemistry={})
    report=['# Can a different representation separate weak structure from nuisance?', '',
        '**Status of this worked investigation.** The author already knew the virtual-PDF idea. This execution demonstrates one admissible evidence-building workflow; '
        'it is not evidence that an investigator or agent independently discovered that idea. Naming a transform alone is not the scientific result.', '',
        '**Initial hypotheses.** Strong peaks may dominate similarity while weak peaks distinguish otherwise similar phases. '
        'Intensity compression could expose those weak distinctions, but may also amplify weak noise and background. '
        'A second hypothesis is that broad smooth background occupies a separable part of a physically defined representation. '
        'I compare raw intensities, signed square-root compression, broad-background subtraction, a smoothed derivative, and several windows of a Q-weighted sine transform. '
        'All alternatives use the same ridge classifier family so that classifier choice is not the explanation for differences.', '',
        '**Physical construction and numerical choices.** Interpolate to 2,001 angle samples over 10.02–79.98 degrees, subtract each spectrum\'s tenth percentile and divide by its peak, retaining negative residuals. '
        'Use unit L2 feature normalization. With wavelength 1.5406 Å and theta half the recorded two-theta angle, define Q=4pi sin(theta)/lambda and '
        'G(r)=(2/pi) integral Q I(Q) sin(Qr)dQ. The quadrature uses the actual nonuniform Q spacings. '
        'The sine basis connects scattering-vector variation to real-space distance, but the absent physical corrections mean G is a virtual, uncorrected PDF. '
        'A background varying slowly in Q is expected mainly at short distances, while sharper diffraction structure can survive at larger distances; '
        'Q weighting also changes the relative influence of angular regions. Finite support can leak artifacts across windows, so this physical argument needs numerical checking. '
        'It is evaluated at 1,191 distances over 1–120 Å; windows 1–5, 5–40, 1–40, and 40–120 Å test localization and signal loss. '
        'Angular truncation deliberately limits this baseline; higher-angle data and other preprocessing choices are not explored.', '',
        '**Separation of selection from evaluation.** Phase-stratified training, validation and test repeats are disjoint. '
        'Templates and nearest-phase hypotheses use training only. Each candidate classifier is trained on clean released training spectra; '
        'regularization and representation are selected using clean/noise/background validation performance, giving the three artifact families equal weight. '
        'Synthetic artifacts are independently generated for validation and test. Here clean means no additional corruption; the release already includes simulated artifacts. '
        'After selection, all alternatives are evaluated on the same held-out spectra. Test labels are used only for scoring and interpretation.', '']
    figure,axes=plt.subplots(1,2,figsize=(14,5))
    mechanism_fig,mechanism_axes=plt.subplots(2,2,figsize=(13,8))
    for chemindex,chemistry in enumerate(CHEMS):
        rows,values=load(inputs,chemistry)
        labels,roles=split(rows)
        training,validation,test=[roles==role for role in ['train','validation','test']]
        classes=np.array(sorted(set(labels)))
        splits += [dict(id=row['id'],role=str(role),fold='0') for row,role in zip(rows,roles)]
        train_features=features(values[training])
        validation_arrays={row['condition']:perturb(values[validation],row['condition'],SEED+chemindex*10000+1000+i*10) for i,row in enumerate(CONDITIONS)}
        validation_features={name:features(array) for name,array in validation_arrays.items()}
        models,selections={},{}
        for method in METHODS:
            searched=[]
            for alpha in [.01,.1,1.,10.]:
                classifier=RidgeClassifier(alpha=alpha,solver='cholesky').fit(unit(train_features[method]),labels[training])
                scores={name:float(np.mean(classifier.predict(unit(allfeatures[method]))==labels[validation])) for name,allfeatures in validation_features.items()}
                searched.append((balanced_average(scores),alpha,classifier,scores))
            best=max(searched,key=lambda result:result[0])
            models[method]=best[2]
            selections[method]=dict(alpha=best[1],validation_balanced_accuracy=best[0],validation_condition_accuracy=best[3],
                search=[dict(alpha=item[1],balanced_accuracy=item[0]) for item in searched])
        selected=max(METHODS,key=lambda method:selections[method]['validation_balanced_accuracy'])
        design['chemistry'][chemistry]=dict(selected_method=selected,selection=selections)
        # No test target values have been consulted above this point.
        weak,pair=weak_pairs(chemistry,values,labels,training)
        weak_records += weak
        raw_validation=models['raw_xrd'].predict(unit(validation_features['baseline']['raw_xrd']))
        raw_confusions=Counter((str(truth),str(guess)) for truth,guess in zip(labels[validation],raw_validation) if truth!=guess)
        ablated,ablation_masks=peak_ablation(chemistry,models['raw_xrd'],values[validation],labels[validation])
        ablations+=ablated
        ablation_ids.extend([row['id'] for row,use in zip(rows,validation) if use][:12])
        ablation_clean.append(values[validation][:12]);ablation_strong.append(ablation_masks['strong']);ablation_weak.append(ablation_masks['weak']);ablation_random.append(ablation_masks['random'])
        report += [f'## {chemistry}', '',
            f'**Training evidence.** The closest training-template pair is {pair[0]} / {pair[1]}, raw cosine similarity {weak[0]["raw_cosine"]:.4f}. '
            f'Regions where both templates are below 20% peak occupy {weak[0]["weak_region_fraction"]:.1%} of sampled angles but contain {weak[0]["fraction_difference_energy_below_20percent_peak"]:.1%} of their squared difference. '
            'This measures the actual support for the weak-feature hypothesis; low energy here would limit that explanation. '
            'The corresponding feature-space similarities for all alternatives and the three closest pairs are in training_pair_diagnostics.csv.',
            f'Clean raw-XRD validation confusions (up to five): {raw_confusions.most_common(5)}.',
            f'**Direct reliance diagnostic.** Setting the strongest 10% of angular channels in each validation spectrum to zero changes raw-XRD accuracy by {ablated[0]["accuracy_change"]:+.3f}; '
            f'removing the weakest 10% changes it by {ablated[1]["accuracy_change"]:+.3f}; removing a matched random 10% changes it by {ablated[2]["accuracy_change"]:+.3f} on average across 20 draws. '
            'Masks depend only on observed intensity, never the phase label; the fixed classifier is rescored after feature normalization. '
            'This artificial deletion intervention tests reliance on intense channels more directly than template similarity does. '
            'It also removes physical information, so it cannot by itself establish that such reliance is excessive or that compression should help.',
            f'**Selection before test.** {DISPLAY[selected]} was selected with balanced validation accuracy {selections[selected]["validation_balanced_accuracy"]:.3f}. '
            'All validation scores and alpha searches are in design.json; no method is assumed to win because of its name.', '']
        left,right=mechanism_axes[chemindex]
        left.plot(THETA,pair[2],label=pair[0],linewidth=.8);left.plot(THETA,pair[3],label=pair[1],linewidth=.8,alpha=.8)
        left.set(title=f'{chemistry}: closest training pair',xlabel='Two-theta / degrees',ylabel='Scaled mean intensity');left.legend(fontsize=8)
        clean_pdf=validation_arrays['baseline']@KERNEL.T
        for artifact in ['noise','background']:
            family=[row['condition'] for row in CONDITIONS if row['artifact']==artifact]
            energy=[]
            for method,mask in MASKS.items():
                distances=[];fractions=[]
                for condition in family:
                    delta=(validation_arrays[condition]-validation_arrays['baseline'])@KERNEL.T
                    distances.extend(np.linalg.norm(delta[:,mask],axis=1)/np.maximum(np.linalg.norm(clean_pdf[:,mask],axis=1),1e-30))
                    fractions.extend(np.sum(delta[:,mask]**2,axis=1)/np.maximum(np.sum(delta**2,axis=1),1e-30))
                signal=float(np.mean(np.sum(clean_pdf[:,mask]**2,axis=1)/np.maximum(np.sum(clean_pdf**2,axis=1),1e-30)))
                localization.append(dict(chemistry=chemistry,artifact=artifact,window=method,mean_relative_l2=float(np.mean(distances)),mean_artifact_energy_fraction=float(np.mean(fractions)),mean_signal_energy_fraction=signal))
                energy.append(float(np.mean(fractions)))
            right.plot([DISPLAY[name] for name in WINDOWS],energy,'o-',label=artifact)
        right.set(title=f'{chemistry}: validation artifact localization',ylabel='Fraction of artifact energy',ylim=(0,1.03));right.tick_params(axis='x',rotation=25);right.legend()
        testrows=[row for row,used in zip(rows,test) if used]
        test_guesses={};test_arrays=[]
        for cindex,condition in enumerate(CONDITIONS):
            name=condition['condition']
            changed=perturb(values[test],name,SEED+chemindex*10000+2000+cindex*10)
            tested_features=features(changed)
            if name!='baseline':test_arrays.append(changed[:12])
            for method in METHODS:
                guessed=models[method].predict(unit(tested_features[method]))
                test_guesses[(method,name)]=guessed
                predictions += [dict(id=row['id'],method=method,condition=name,fold='0',predicted=json.dumps([str(guess)])) for row,guess in zip(testrows,guessed)]
                accuracy=float(np.mean(guessed==labels[test]))
                metrics.append(dict(chemistry=chemistry,method=method,condition=name,accuracy=accuracy,n=len(testrows)))
                for (truth,guess),count in Counter((str(truth),str(guess)) for truth,guess in zip(labels[test],guessed) if truth!=guess).items():
                    confusions.append(dict(chemistry=chemistry,method=method,condition=name,truth=truth,predicted=guess,count=count))
        evidence_ids.extend(row['id'] for row in testrows[:12]);evidence_clean.append(values[test][:12]);evidence_changed.append(np.stack(test_arrays))
        axis=axes[chemindex]
        artifact_test={}
        for artifact in ['clean','noise','background']:
            names=[row['condition'] for row in CONDITIONS if row['artifact']==artifact]
            accuracies=[]
            for method in METHODS:
                correctness=np.mean([(test_guesses[(method,name)]==labels[test]).astype(float) for name in names],axis=0)
                accuracies.append(float(correctness.mean()))
                if method!='raw_xrd':
                    baseline=np.mean([(test_guesses[('raw_xrd',name)]==labels[test]).astype(float) for name in names],axis=0)
                    uncertainty.append(dict(chemistry=chemistry,artifact=artifact,method=method,contrast='minus_raw_xrd',**interval(correctness-baseline,labels[test])))
            artifact_test[artifact]=dict(zip(METHODS,accuracies))
            axis.plot(range(len(METHODS)),accuracies,'o-',label=artifact)
        axis.set(title=chemistry,ylabel='Held-out accuracy',ylim=(0,1.03),xticks=range(len(METHODS)),xticklabels=[DISPLAY[name] for name in METHODS]);axis.tick_params(axis='x',rotation=55);axis.legend()
        for method in METHODS:
            scores=[artifact_test[artifact][method] for artifact in ['clean','noise','background']]
            report.append(f'{DISPLAY[method]}: validation balanced {selections[method]["validation_balanced_accuracy"]:.3f}; held-out clean/noise/background accuracy {scores[0]:.3f}/{scores[1]:.3f}/{scores[2]:.3f}.')
        report.append('')
        for artifact in ['clean','noise','background']:
            contrast=next((row for row in uncertainty if row['chemistry']==chemistry and row['artifact']==artifact and row['method']==selected),None)
            if contrast:
                report.append(f'Selected-method minus raw-XRD accuracy for {artifact}: {contrast["estimate"]:+.3f}, phase-block bootstrap 95% interval [{contrast["ci95"][0]:+.3f},{contrast["ci95"][1]:+.3f}].')
        pdfbest=max(WINDOWS,key=lambda method:selections[method]['validation_balanced_accuracy'])
        nonpdfbest=max(METHODS[:4],key=lambda method:selections[method]['validation_balanced_accuracy'])
        report += [f'The best validation-selected virtual-PDF window is {DISPLAY[pdfbest]}, and the best non-PDF alternative is {DISPLAY[nonpdfbest]}. '
            f'Their held-out background accuracies are {artifact_test["background"][pdfbest]:.3f} and{artifact_test["background"][nonpdfbest]:.3f}, respectively. '
            'Thus the physical transform must be judged against an effective simpler competitor, not only against untreated intensities.', '']
        for artifact in ['clean','noise','background']:
            names=[row['condition'] for row in CONDITIONS if row['artifact']==artifact]
            delta=np.mean([(test_guesses[(pdfbest,name)]==labels[test]).astype(float)-(test_guesses[(nonpdfbest,name)]==labels[test]).astype(float) for name in names],axis=0)
            comparison=dict(chemistry=chemistry,artifact=artifact,method=pdfbest,contrast=f'minus_{nonpdfbest}',**interval(delta,labels[test]))
            uncertainty.append(comparison)
            report.append(f'Validation-selected PDF minus validation-selected non-PDF accuracy for {artifact}: {comparison["estimate"]:+.3f}, phase-block 95% interval [{comparison["ci95"][0]:+.3f}, {comparison["ci95"][1]:+.3f}].')
        selected_localization=next(row for row in localization if row['chemistry']==chemistry and row['artifact']=='background' and row['window']==pdfbest)
        report.append(f'The selected PDF window retains {selected_localization["mean_signal_energy_fraction"]:.1%} of sampled clean-signal energy but only {selected_localization["mean_artifact_energy_fraction"]:.3%} of added smooth-background energy on validation spectra. '
            'Together with its held-out background result, this supports the nuisance-localization mechanism for these constructed backgrounds. '
            f'Signed square-root compression changes held-out clean accuracy by {artifact_test["clean"]["sqrt_xrd"]-artifact_test["clean"]["raw_xrd"]:+.3f} relative to raw XRD; '
            'the weak-feature hypothesis does not by itself justify compression as an effective remedy.')
        selected_errors=Counter((str(truth),str(guess)) for truth,guess in zip(labels[test],test_guesses[(selected,'baseline')]) if truth!=guess)
        report.append(f'Clean selected-method held-out confusions (up to five): {selected_errors.most_common(5)}. These were inspected only after final selection; confusion_counts.csv retains every condition and method.')
        report.append('')
    background_gains=[row for row in uncertainty if row['artifact']=='background' and row['contrast']=='minus_raw_xrd' and row['method']==design['chemistry'][row['chemistry']]['selected_method']]
    credible_background=sum(row['ci95'][0]>0 for row in background_gains)
    competitor_gains=[row for row in uncertainty if row['artifact']=='background' and row['contrast'].startswith('minus_') and row['contrast']!='minus_raw_xrd']
    credible_competitor=sum(row['ci95'][0]>0 for row in competitor_gains)
    report += ['## What the experiment supports', '',
        f'The validation-selected method improves background-corrupted accuracy over raw XRD with a positive paired interval in {credible_background} of {len(background_gains)} chemistries. '
        f'Against the validation-selected non-PDF competitor, the best PDF window has a positive background-accuracy interval in {credible_competitor} of {len(competitor_gains)} chemistries. '
        'The principal evidence concerns smooth-background robustness. Small clean/noise differences must be read with their intervals and do not establish a broad superiority claim. '
        'Removing intense channels confirms that raw classification relies on them, but weaker performance after compression shows why reliance alone is not a diagnosis of avoidable error.', '',
        'The physically defined transform and a distance-window search constitute an implemented representation proposal. '
        'Whether that proposal is useful is a separate empirical claim: use the held-out comparisons above, including the non-PDF alternatives and the paired uncertainty. '
        'Signed compression, high-pass filtering and derivatives test competing explanations for any gain. '
        'Training-template differences test whether weak intensities actually distinguish near-neighbor phases; validation artifact-energy localization tests the proposed separation mechanism. '
        'Neither diagnostic alone proves an accuracy improvement. The classification results are the functional check.', '',
        'The saved validation_localization.csv quantifies smooth-background/noise energy and retained signal in each distance window. '
        'The eigenstructure of the finite sampled transform and truncation matter: this is an information reweighting and filtering experiment, not creation of new information. '
        'A useful window can suppress background while retaining enough phase distinction, but it can also discard discriminative signal. '
        'A representation that loses to a simpler alternative still provides a valid negative finding.', '',
        '## Uncertainty, limitations and reproducibility', '',
        'Paired confidence intervals use 2,000 bootstrap resamples of phase identities, carrying their repeated test spectra together. '
        'Condition severities and noise draws are averaged within each spectrum before resampling. '
        'The intervals condition on one training/validation split and do not include selection or retraining uncertainty. '
        'Boundary empirical intervals may collapse and do not establish certainty for future specimens. '
        'The benchmark tests augmented repeats of represented structures, not unseen phases or measured specimens. '
        'Synthetic Gaussian noise and broad backgrounds span only two severities and are controlled mechanisms, not comprehensive instrument models. '
        'All methods use one learner family and modest searches; this does not establish universal representation superiority or a global optimum.', '',
        'predictions.csv, splits.csv and conditions.csv allow independent label-based scoring. '
        'metrics.csv is a convenience summary; uncertainty.json records paired contrasts. '
        'design.json records all validation searches and selections. '
        'evidence.npz saves the first 12 held-out IDs per chemistry, their clean/perturbed preprocessed XRD, corresponding full 1–120 Å virtual PDFs, and axes. '
        'Perturbed arrays have axes(condition,sample,feature), with baseline omitted from the condition list. '
        'Additional ablation_ids and ablation_clean_xrd contain twelve validation records per chemistry; ablation_strong_masks and ablation_weak_masks are(sample,angle), '
        'and ablation_random_masks is(draw,sample,angle). A true mask entry sets that observed intensity to zero. '
        'validation_ablation.csv retains full-validation accuracy and true-class decision-margin changes. '
        'These audit IDs were fixed before examining outcomes; all spectra were evaluated. '
        'run.py reconstructs every generated array and result using only the supplied four raw input files.']
    clean=np.concatenate(evidence_clean);changed=np.concatenate(evidence_changed,axis=1)
    np.savez_compressed(out/'evidence.npz',theta=THETA,r=R,ids=np.array(evidence_ids),conditions=np.array([row['condition'] for row in CONDITIONS if row['condition']!='baseline']),
        clean_xrd=clean,perturbed_xrd=changed,clean_pdf=clean@KERNEL.T,perturbed_pdf=changed@KERNEL.T,
        ablation_ids=np.array(ablation_ids),ablation_clean_xrd=np.concatenate(ablation_clean),
        ablation_strong_masks=np.concatenate(ablation_strong),ablation_weak_masks=np.concatenate(ablation_weak),ablation_random_masks=np.concatenate(ablation_random,axis=1))
    csvwrite(out/'predictions.csv',predictions)
    csvwrite(out/'splits.csv',splits)
    csvwrite(out/'conditions.csv',CONDITIONS)
    csvwrite(out/'metrics.csv',metrics)
    csvwrite(out/'training_pair_diagnostics.csv',weak_records)
    csvwrite(out/'validation_localization.csv',localization)
    csvwrite(out/'validation_ablation.csv',ablations)
    csvwrite(out/'confusion_counts.csv',confusions,['chemistry','method','condition','truth','predicted','count'])
    write(out/'design.json',design);write(out/'uncertainty.json',uncertainty)
    (out/'report.md').write_text('\n'.join(report)+'\n')
    figure.tight_layout();figure.savefig(out/'diagnostics.png',dpi=150);plt.close(figure)
    mechanism_fig.tight_layout();mechanism_fig.savefig(out/'mechanism.png',dpi=150);plt.close(mechanism_fig)
    shutil.copyfile(__file__,out/'run.py')
    write(out/'execution.json',dict(elapsed_seconds=time.time()-started,candidate_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        numpy=np.__version__,scipy=__import__('scipy').__version__,sklearn=__import__('sklearn').__version__,input_directory=str(inputs.resolve())))
    print(json.dumps(dict(predictions=len(predictions),elapsed_seconds=time.time()-started,selected={chem:design['chemistry'][chem]['selected_method'] for chem in CHEMS})),flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    run(args.inputs,args.output)

if __name__=='__main__':main()
