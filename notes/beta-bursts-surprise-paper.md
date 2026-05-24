# β-bursts Over Frontal Cortex Track the Surprise of Unexpected Events
**Tatz et al., bioRxiv 2022.07.13.499837**

## Paper Metadata
- **Authors:** Joshua R. Tatz, Alec Mather, and colleagues  
- **Affiliation:** Department of Psychological and Brain Sciences, University of Iowa
- **Posted:** July 13, 2022 (preprint)
- **DOI:** https://doi.org/10.1101/2022.07.13.499837
- **URL:** https://www.biorxiv.org/content/10.1101/2022.07.13.499837

## Biological Question
How does the brain detect unexpected sensory events and trigger inhibitory control? Specifically, are brief bursts of β-frequency oscillations (β-bursts) in frontal cortex involved in surprise processing?

## Key Contribution
This is the first study to demonstrate that **β-bursts over frontal cortex increase following unexpected sensory events across visual, auditory, and haptic modalities**, linking β-bursts to reactive (stimulus-driven) inhibitory control rather than just proactive (anticipated) control studied in stop-signal tasks.

## Method
**Experimental Design:**
- Two independent datasets using cross-modal oddball (CMO) tasks
  - **Dataset 1:** 40 participants; trimodal (visual, auditory, haptic) unexpected events  
  - **Dataset 2:** 55 participants; bimodal (visual, auditory) unexpected events; replication/verification sample
  
**Task Structure:**
- 80% standard trials: green circle + 600 Hz tone, participant responds to target arrow
- 20% unexpected trials: novel visual stimuli (unique colors/shapes), novel auditory (birdsongs), or haptic vibration (Dataset 1 only)
- Fixed 500 ms cue-to-target interval (allows expectancy violations)
- Participants pressed buttons/keys based on arrow direction
- Total: 240 trials per person in CMO task

**β-burst Analysis:**
- 62-channel scalp EEG at 500 Hz sampling
- Preprocessing: 0.3–30 Hz bandpass, ICA artifact removal
- β-bursts defined as transient increases in 15–29 Hz power (non-linear, single-trial events)
- Measured post-stimulus β-burst rate and latency
- Compared across standard vs. unexpected trials by modality

**Surprise Quantification:**
- Shannon entropy-based model: surprise = -log(probability of stimulus given context)
- Single-trial surprise estimates derived from theoretical probability model
- Compared to β-burst rate for trial-level correlations

**Baseline Comparison:**
- Stop-Signal Task (SST) included as functional localizer to confirm same frontal β-bursts appear in action-stopping context

## Key Results

### Primary Findings (Datasets 1 & 2 combined):
1. **Unexpected events increase β-bursts over frontal cortex** at low latency (~100–200 ms post-stimulus)
   - Visual: elevated β-bursts
   - Auditory: elevated β-bursts  
   - Haptic: elevated β-bursts (Dataset 1)
   - Effect robust across both datasets

2. **β-burst rate correlates with Shannon surprise estimates** (single-trial analysis)
   - Higher surprise → higher β-burst rate
   - Across all sensory modalities
   - Effect size moderate to large

3. **β-bursts precede and predict behavioral changes**
   - RT slowing following unexpected events
   - Link β-bursts to reactive motor inhibition

### Supporting Evidence:
- **Fronto-Central P3 ERP** (classic marker of unexpected events) also increased following unexpected events, confirming paradigm validity
- **Stop-Signal Task results** confirmed same frontal regions show β-bursts during action cancellation (successful stop trials)
- No evidence of startle response contaminating results (verified via EMG piloting)

## Code & Data
- **GitHub:** Not found in paper or abstract
- **Dataset:** Behavioral and EEG raw data mentioned but access not explicitly specified in text
- **Analysis code:** Custom MATLAB scripts using EEGLAB and Psychtoolbox; reproducibility details provided in Methods

## Replication Status
- **Replicability:** Partial
  - Methods fully described (EEG parameters, task timing, statistical tests)
  - Datasets not immediately publicly available (would need to contact authors)
  - Analysis pipeline documented but custom code would need publication/sharing
  - Strong pre-registration features: two independent datasets used (Dataset 1 exploratory, Dataset 2 confirmatory)

## Theoretical Context
- **Connects two major literatures:**
  1. **Surprise/prediction error processing:** Brain predicts sensory input; violations trigger inhibitory control
  2. **β-bursts as inhibitory signatures:** Recent work on cortical/subcortical β-bursts as transient neural markers of motor inhibition
  
- **Distinguishes reactive vs. proactive control:**
  - Oddball tasks allow pure reactive inhibition (no warning, not task-relevant)
  - Previous β-burst studies mostly in stop-signal context (mixed reactive + proactive)
  - This work isolates reactive inhibitory control triggered by stimulus surprise

## Open Questions & Limitations

1. **Mechanism:** What thalamocortical circuit generates these β-bursts? (hypothesis mentioned but not tested here)
2. **Functional necessity:** Do β-bursts *cause* inhibition or merely correlate with it?
3. **Clinical translation:** How might β-burst signatures differ in ADHD, impulse control disorders, Parkinson's disease?
4. **Cross-species:** Are analogous β-bursts present in rodent/primate models?

## Related Work to Compare
- **Stop-signal task β-bursts:** Wessel (2020), Jana et al. (2020), Diesburg et al. (2021)
- **Surprise/prediction error:** Friston free-energy principle; Mars et al. (2008), O'Reilly et al. (2013)
- **P3 and inhibitory control:** Dutra et al. (2018), Wessel & Huber (2019)
- **Motor suppression after unexpected events:** Wessel et al. (2013), Tatz et al. (2021)

## Citation
```
Tatz, J. R., Mather, A., et al. (2022). β-bursts over frontal cortex track the surprise of unexpected events. 
bioRxiv preprint. https://doi.org/10.1101/2022.07.13.499837
```
