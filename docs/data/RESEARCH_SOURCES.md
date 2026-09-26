# BeatIT Synthetic Data and Runtime Sources

These sources define reference roles only; they are not mixed into synthetic
profile identities.

| Source | Role | Identity policy |
|---|---|---|
| [Synthea](https://github.com/synthetichealth/synthea) | Candidate synthetic FHIR R4 population generator | Not installed/used in this run; local deterministic generator used instead |
| [CDC NHANES](https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?Cycle=2021-2023) | Optional broad population reference | Never copied into BeatIT identities |
| [NHANES BP documentation](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/BPXO_L.htm) | Optional BP measurement/protocol reference | Reference only |
| [PTB-XL v1.0.3](https://physionet.org/content/ptb-xl/1.0.3/) | ECG format/benchmark reference | Never attached to a synthetic patient |
| [NeuroKit2 ECG documentation](https://neuropsychology.github.io/NeuroKit/functions/ecg.html) | Candidate synthetic waveform generator | Not installed; campaign ECGs use a deterministic local waveform generator and are labeled synthetic |
| [Project MONAI VISTA](https://github.com/Project-MONAI/VISTA) | Optional medical-image segmentation runtime/reference | Local checkpoint remains optional and unserved |
| [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-tunnel/) | Public exposure mechanism | Public verification requires a named/managed tunnel and origin-route checks |
