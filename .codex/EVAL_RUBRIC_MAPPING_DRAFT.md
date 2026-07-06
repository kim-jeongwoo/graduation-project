# 27 - Evaluation Rubric Mapping Draft

Date: 2026-05-18
Scope: 4/6~5/10 evaluation material mapping before app-copy changes
Status: draft, privacy-preserving

## 1. Scope And Privacy Rules

- This document is a `.codex` scratch artifact, not a GitHub release artifact.
- Do not copy original DOCX text in full.
- Do not report student names, evaluator names, contact details, accounts, or raw identifying audio filenames.
- WAV/MIDI files were counted only. They were not opened, played, or analyzed.
- DOCX files are referenced as anonymous evaluation forms or criteria sheets.

## 2. Source Inventory

| Location | Files confirmed | Notes |
|---|---:|---|
| `/Users/kimjeongwoo/Downloads/평가자료(5:10)/` | 5 DOCX, 21 WAV, 6 MID, 1 no-extension file | Primary 5/10 material. DOCX forms are score sheets. |
| `/Users/kimjeongwoo/Desktop/졸업작품/녹음본 및 평가표/평가자료(5:10)/` | 5 DOCX, 21 WAV, 6 MID, 1 no-extension file | Mirror candidate. DOCX text matches primary set; 2 DOCX differ at package/metadata level. |
| `/Users/kimjeongwoo/Desktop/졸업작품/녹음본 및 평가표/` | 28 DOCX, 202 WAV, 6 MID, 1 ZIP, 4 no-extension files | Broader archive. Includes evaluator criteria sheets and duplicate score forms. |

Findings:
- The five 5/10 DOCX evaluation forms use a 9-item, 0-5 numeric score table.
- The five forms do not contain full item-by-item textual rubric definitions; they point to a separate criteria sheet.
- The separate evaluator criteria sheet defines `0~1 = 미달`, `2~3 = 적절`, `4~5 = 과함`.
- A/B style recording labels exist in the score forms, but this draft does not expose raw recording/song/person identifiers.

## 3. App Current Mapping Snapshot

| app key | app display name | current status | app source |
|---|---|---|---|
| `breathiness` | 호흡 소리 식별 | active 4-item flow | `EvalResultScreen`, `TrainingScreen`, `weakSections` |
| `vocal_fold_contact` | 성대 접촉 강도 | active 4-item flow | `EvalResultScreen`, `TrainingScreen`, `weakSections` |
| `soft_palate` | 연구개 위치 | active 4-item flow, v2 fallback copy exists | `EvalResultScreen`, `TrainingScreen`, `weakSections` |
| `tongue_tension` | 혀/구강 공간 경직도 | active 4-item flow, v2 fallback copy exists | `EvalResultScreen`, `TrainingScreen`, `weakSections` |
| `nasal_oral_ratio` | 비강/구강 공명 비율 | inactive/reference | `EvalResultScreen`, `evaluationItems` |
| `chest_head_voice` | 흉성/두성 경향 | inactive/reference | `EvalResultScreen`, `evaluationItems` |
| `forward_resonance` | 전방 공명 정도 | inactive/reference | `EvalResultScreen`, `evaluationItems` |
| `pressure_balance` | 상압/하압 비율 | inactive/reference | `EvalResultScreen`, `evaluationItems` |
| `larynx_tongue_root` | 공명 개방감 | inactive/reference | `EvalResultScreen`, `evaluationItems` |

Current app zone convention:
- `insufficient`: 0-1
- `appropriate`: 2-3
- `excessive`: 4-5

## 4. 9-Item Rubric Mapping

| app key | app display name | criteria item | confidence | criteria band summary | app-copy conflict risk | copy readiness |
|---|---|---|---|---|---|---|
| `nasal_oral_ratio` | 비강/구강 공명 비율 | 비강, 구강 공명의 비율 | high | 0-1: nasal-heavy; 2-3: balanced/natural; 4-5: oral-heavy or lack of nasal resonance | Medium: score direction is two-sided, not simply more nasal is higher. | Expert review |
| `chest_head_voice` | 흉성/두성 경향 | 흉성/두성 경향 | high | 0-1: head-dominant/light; 2-3: balanced mix; 4-5: chest-dominant/heavy | Low to medium. Current app description is broad and compatible. | Draftable |
| `vocal_fold_contact` | 성대 접촉 강도 | 성대 접촉 강도 | high | 0-1: weak contact/breathy/unstable; 2-3: light-to-stable contact; 4-5: strong/pressed/rough contact | Low. Current active copy is generic but directionally compatible. | Draftable |
| `breathiness` | 호흡 소리 식별 | 호흡 소리 식별 | high | 0-1: breath sound too prominent; 2-3: some/needed breath; 4-5: little breath, dense/compressed sound | High: app currently says low/high breathiness, but rubric low score means too much breath. | Expert review before app copy |
| `forward_resonance` | 전방 공명 정도 | 소리의 전방 공명 정도 | high | 0-1: too far forward/sharp; 2-3: clear/stable; 4-5: too far back/dark | High: key name suggests forward amount, but rubric score direction moves from too-forward to too-back. | Expert review |
| `soft_palate` | 연구개 위치 | 연구개의 위치 | high | 0-1: low/down/narrow; 2-3: natural/stable space; 4-5: high/tension/stiffness | Medium: current copy is mostly aligned, but 2 vs 3 wording has low/high nuance. | Draftable with review |
| `larynx_tongue_root` | 공명 개방감 | 후두, 혀뿌리의 위치 | high | 0-1: high larynx/tongue-root tension/narrow; 2-3: stable/open; 4-5: low/heavy/dark/stiff | Medium: app display name is broader than criteria item. Inactive mode label is closer. | Expert review |
| `tongue_tension` | 혀/구강 공간 경직도 | 혀, 구강 공간의 경직도 | high | 0-1: low support/loose/unclear articulation; 2-3: flexible/natural/clear; 4-5: strong tension/dull or smeared articulation | Medium: current insufficient copy partly fits, but "do not press too much" may sound like excessive tension. | Draftable with review |
| `pressure_balance` | 상압/하압 비율 | 상압/하압 비율 | high | 0-1: upper-pressure leaning/light/unsupported; 2-3: balanced/efficient; 4-5: lower-pressure leaning/pushed/rough | Low to medium. Current app description is broad and compatible. | Draftable |

## 5. Active 4 Items Zone Draft

These are rubric summaries for mapping only, not final app copy.

| app key | insufficient 0-1 | appropriate 2-3 | excessive 4-5 | current app conflict | candidate direction |
|---|---|---|---|---|---|
| `breathiness` | breath sound is too prominent; voice may sound airy or unclear | slight/needed breath is mixed naturally | breath sound is nearly absent; sound may be dense or compressed | Current low/high wording can be misleading because low score means too much breath, not too little breath. | Use two-sided language: too airy vs too compressed. Expert review required. |
| `vocal_fold_contact` | contact is weak; sound may be airy, unstable, or shaky | contact is light-to-stable and clear | contact is strong; sound may be pressed, stiff, or rough | Current low/high wording is directionally safe but too generic. | Can draft clearer low/stable/pressed copy. |
| `soft_palate` | palate/inner space is low or narrow; sound can feel closed | inner space is natural/stable and resonance is supported | palate/space may be overly lifted or tense/stiff | Current copy generally matches, but "raise the palate" instruction for low score needs expert tone check. | Draft carefully as space/naturalness, not mechanical diagnosis. |
| `tongue_tension` | tongue/oral support may be too loose; articulation can be unclear | oral space is flexible and articulation is natural/clear | tongue/oral space may be tense; articulation can sound dull or smeared | Current insufficient copy is close, but mentions not pressing too much, which belongs more to excessive tension. | Split low-support vs excessive-tension language. |

## 6. Inactive 5 Items Check

| app key | criteria mapping | current app description conflict | immediate app-copy need |
|---|---|---|---|
| `nasal_oral_ratio` | clear mapping exists | Medium. The score direction is two-sided and should not be simplified to "more nasal = higher". | No immediate change; expert review first. |
| `chest_head_voice` | clear mapping exists | Low. Broad app description is compatible. | No immediate change while inactive. |
| `forward_resonance` | clear mapping exists | High. Criteria low score means too-forward, high score means too-back; app key/display may imply the opposite. | Do not finalize copy without expert review. |
| `pressure_balance` | clear mapping exists | Low to medium. Broad app description is compatible if score direction is documented. | No immediate change while inactive. |
| `larynx_tongue_root` | clear mapping exists | Medium. App display `공명 개방감` is broad; criteria names larynx/tongue-root position. | Keep inactive/reference; consider label consistency later. |

## 7. Conflicts And Risks

- The five 5/10 evaluation DOCX forms contain numeric scores, not the full rubric text. The zone language comes from the separate criteria sheet.
- `breathiness` has the highest active-copy risk: score 0-1 means breath is too audible, while app wording can be read as "breathiness is low".
- `forward_resonance` has the highest inactive-copy risk: score direction appears to move from too-forward to too-back.
- `tongue_tension` low-score copy should not sound like high-tension coaching.
- `larynx_tongue_root` display-name consistency should be reviewed before user-facing copy changes.
- The criteria sheet is pedagogical rubric text, not proof that current model score distributions match expert judgments. Score distribution validation is a separate dml-server/model task.

## 8. Copy Candidates

Immediately draftable for review:
- `vocal_fold_contact`: weak contact / stable contact / pressed contact.
- `soft_palate`: narrow or low inner space / stable space / tense or over-lifted space.
- `tongue_tension`: low oral support or unclear articulation / flexible clear articulation / excessive tension or smeared articulation.
- `pressure_balance`, `chest_head_voice`: broad reference copy can be drafted while they remain inactive.

Needs representative/expert confirmation before app copy:
- `breathiness`: whether app should describe 0-1 as "숨이 많이 섞임" rather than "낮음".
- `forward_resonance`: whether high score should be described as back/dark resonance in app copy.
- `nasal_oral_ratio`: whether 0-1 and 4-5 should be treated as opposite imbalance directions rather than a single high/low continuum.
- `larynx_tongue_root`: whether user-facing label should remain `공명 개방감` or align with `후두/혀뿌리 위치`.
- Whether the criteria sheet ver.3 should supersede ver.2 where wording differs.

## 9. Recommended Next Task

Recommended: B. `28 - 대표님 검토용 피드백 문구 초안 작성`.

Reason:
- Mapping is strong enough to prepare a review draft.
- Direct app reflection is premature because at least `breathiness`, `forward_resonance`, and `nasal_oral_ratio` need score-direction confirmation.
- The next draft should remain review-only until representative/expert approval.

GitHub status:
- No commit, push, PR, merge, reset, revert, or delete action in task 27.
- No app feature code change in task 27.
