# Research and policy references

## Scope and use

This bibliography supports BeatIT's problem framing and design boundaries. It
does not constitute clinical validation of BeatIT, endorsement of its formulas,
or evidence that the software improves care. Repository formulas and model
assumptions require their own verification and, before clinical use,
fit-for-purpose validation.

Links were checked during the documentation audit on 2026-09-26. DOI links are
preferred for durable scholarly references.

## Cardiovascular burden

1. World Health Organization.
   [Cardiovascular diseases (CVDs)](https://www.who.int/news-room/fact-sheets/detail/cardiovascular-diseases-(cvds)).
   Reports global burden and major risk factors. Used only to establish public
   health context.
2. US Centers for Disease Control and Prevention.
   [Heart Disease Facts](https://www.cdc.gov/heart-disease/data-research/facts-stats/index.html).
   US burden and mortality context.

## Cardiac digital twins and patient-specific modeling

1. Corral-Acero J, et al.
   [The “Digital Twin” to enable the vision of precision cardiology](https://doi.org/10.1093/eurheartj/ehaa159).
   *European Heart Journal*. 2020;41(48):4556–4564.
   Reviews the cardiovascular digital-twin vision and translational challenges.
2. Niederer SA, et al.
   [Creation and application of virtual patient cohorts of heart models](https://doi.org/10.1098/rsta.2019.0580).
   *Philosophical Transactions of the Royal Society A*. 2020;378:20190580.
   Discusses virtual cohorts, variability, and computational experiment design.
3. Viceconti M, Henney A, Morley-Fletcher E.
   [In silico clinical trials: how computer simulation will transform the biomedical industry](https://doi.org/10.18203/2349-3259.ijct20161408).
   *International Journal of Clinical Trials*. 2016;3(2):37–46.
   Background on in-silico evidence; it does not justify calling BeatIT's
   paired simulations clinical trials.
4. Viceconti M, et al.
   [In silico trials: Verification, validation and uncertainty quantification of predictive models used in the regulatory evaluation of biomedical products](https://doi.org/10.1016/j.ymeth.2020.01.011).
   *Methods*. 2021;185:120–127.
   Relevant to verification, validation, and uncertainty terminology.

## Uncertainty, verification, and model credibility

1. National Academies of Sciences, Engineering, and Medicine.
   [Assessing the Reliability of Complex Models: Mathematical and Statistical Foundations of Verification, Validation, and Uncertainty Quantification](https://doi.org/10.17226/13395).
   National Academies Press; 2012.
   General VVUQ foundation.
2. ASME.
   *V&V 40: Assessing Credibility of Computational Modeling through
   Verification and Validation—Application to Medical Devices*.
   2018.
   Risk-informed credibility framework; BeatIT does not claim conformance.
3. US Food and Drug Administration.
   [Assessing the Credibility of Computational Modeling and Simulation in Medical Device Submissions](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/assessing-credibility-computational-modeling-and-simulation-medical-device-submissions).
   Guidance; 2023.
   Relevant if future claims enter a regulated medical-device context.

## Cardiac measurements and anatomy

1. Lang RM, et al.
   [Recommendations for Cardiac Chamber Quantification by Echocardiography in Adults](https://doi.org/10.1016/j.echo.2014.10.003).
   *Journal of the American Society of Echocardiography*. 2015;28(1):1–39.e14.
   Clinical chamber-measurement conventions; citation does not validate
   BeatIT's simplified simulation.
2. Cerqueira MD, et al.
   [Standardized Myocardial Segmentation and Nomenclature for Tomographic Imaging of the Heart](https://doi.org/10.1161/hc0402.102975).
   *Circulation*. 2002;105(4):539–542.
   Source for the AHA 17-segment nomenclature used by the findings layer.
3. Mosteller RD.
   [Simplified Calculation of Body-Surface Area](https://pubmed.ncbi.nlm.nih.gov/3657876/).
   *New England Journal of Medicine*. 1987;317:1098.
4. Bazett HC.
   [An analysis of the time-relations of electrocardiograms](https://doi.org/10.1111/j.1542-474X.1997.tb00325.x).
   *Heart*. 1920;7:353–370.
   Historical QT-correction basis, linked through a later republication; known
   rate-dependent limitations should not be hidden.

## Medical imaging and VISTA-3D

1. Butoi VI, et al.
   [VISTA3D: Versatile Imaging SegmenTation and Annotation model for 3D medical imaging](https://arxiv.org/abs/2406.05285).
   arXiv:2406.05285 (2024).
   Describes the optional model family. A local checkpoint or adapter is not
   evidence of live service availability or clinical performance in BeatIT.
2. MONAI Consortium.
   [MONAI documentation](https://docs.monai.io/).
   Framework documentation for medical-imaging model execution.

## Language models and health AI

1. Singhal K, et al.
   [Large language models encode clinical knowledge](https://doi.org/10.1038/s41586-023-06291-2).
   *Nature*. 2023;620:172–180.
   Demonstrates capability while discussing evaluation and limitations; it
   does not support using an LLM as BeatIT's numerical authority.
2. World Health Organization.
   [Ethics and governance of artificial intelligence for health](https://www.who.int/publications/i/item/9789240029200).
   2021.
   Addresses autonomy, safety, transparency, accountability, equity, and
   sustainability.
3. World Health Organization.
   [Ethics and governance of artificial intelligence for health: guidance on large multi-modal models](https://www.who.int/publications/i/item/9789240084759).
   2024.
   Governance considerations for generative and multimodal systems.

## Clinical decision support, human factors, and regulation

1. US Food and Drug Administration.
   [Clinical Decision Support Software: Guidance for Industry and FDA Staff](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software).
   2022.
2. US Food and Drug Administration.
   [Applying Human Factors and Usability Engineering to Medical Devices](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/applying-human-factors-and-usability-engineering-medical-devices).
   2016.
3. US Food and Drug Administration.
   [Software as a Medical Device (SaMD)](https://www.fda.gov/medical-devices/digital-health-center-excellence/software-medical-device-samd).
4. International Medical Device Regulators Forum.
   [Software as a Medical Device: Clinical Evaluation](https://www.imdrf.org/documents/software-medical-device-samd-clinical-evaluation).
   IMDRF/SaMD WG/N41FINAL:2017.

These sources frame future assessment. BeatIT has no claimed FDA clearance,
approval, authorization, or established non-device determination.

## Interoperability, privacy, and data governance

1. HL7 International.
   [FHIR overview](https://www.hl7.org/fhir/overview.html).
   Standard context for the repository's FHIR ingestion code.
2. US Assistant Secretary for Technology Policy / Office of the National
   Coordinator for Health IT.
   [Health Information Exchange](https://www.healthit.gov/topic/health-it-and-health-information-exchange-basics/health-information-exchange).
3. US Department of Health and Human Services.
   [HIPAA Privacy Rule](https://www.hhs.gov/hipaa/for-professionals/privacy/index.html).
4. US Department of Health and Human Services.
   [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html).
5. US Department of Health and Human Services.
   [Methods for De-identification of Protected Health Information](https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html).

These references do not make a deployment HIPAA compliant. Applicability and
compliance depend on the organization, data, contracts, controls, and use.

## Datasets represented in repository adapters or local campaign records

1. Wagner P, et al.
   [PTB-XL, a large publicly available electrocardiography dataset](https://doi.org/10.1038/s41597-020-0495-6).
   *Scientific Data*. 2020;7:154.
   Dataset: [PhysioNet PTB-XL](https://physionet.org/content/ptb-xl/).
2. Chicco D, Jurman G.
   [Machine learning can predict survival of patients with heart failure from serum creatinine and ejection fraction alone](https://doi.org/10.1186/s12911-020-1023-5).
   *BMC Medical Informatics and Decision Making*. 2020;20:16.
   Dataset: [UCI Heart Failure Clinical Records](https://archive.ics.uci.edu/dataset/519/heart+failure+clinical+records).
3. Bernard O, et al.
   [Deep Learning Techniques for Automatic MRI Cardiac Multi-structures Segmentation and Diagnosis: Is the Problem Solved?](https://doi.org/10.1109/TMI.2018.2837502).
   *IEEE Transactions on Medical Imaging*. 2018;37(11):2514–2525.
   Describes CAMUS. Repository records currently mark its public-demo use
   no-go pending license/terms clarification and do not wire pixels into the
   product.
4. Johnson AEW, et al.
   [MIMIC-IV, a freely accessible electronic health record dataset](https://doi.org/10.1038/s41597-022-01899-x).
   *Scientific Data*. 2023;10:1.
   Credentialed MIMIC data are not a public BeatIT demo asset; repository
   records use only the separately governed demo where permitted.

Datasets contain different subjects and modalities. BeatIT must not imply that
records from separate datasets belong to one person. Dataset licenses and
data-use terms govern any redistribution or public demonstration.
