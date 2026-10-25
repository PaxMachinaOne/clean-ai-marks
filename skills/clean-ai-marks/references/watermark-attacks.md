# Statistical watermarks

The job of this skill is to scramble and blur a **statistical** text watermark. Nothing else in this file is that job.

A statistical watermark (Kirchenbauer green-list, SynthID-Text tournament sampling, Claude's embedded text watermark) is a bias on the next token. It is not a hidden character, not a C2PA manifest, and not a visible stamp. Scrambling changes which tokens are chosen and, on a stronger pass, the order they appear in. Blurring is the same change from the detector's side: the green-list score falls because the tokens moved. One pass does not prove the score is below a detector's threshold. A unigram watermark often survives a single paraphrase.

## How the scramble is done

The published query-free baselines are:

- **Lexical diversity.** Replace wording and keep sentence order. This is `--strength paraphrase`. It is the lexical knob of DIPPER (Krishna et al., 2023).
- **Back-translation.** Translate out and back. This is `--strength backtranslate`, the attack used in the Kirchenbauer robustness evaluation.
- **Order diversity plus regeneration.** Split, merge, and reorder, or rebuild from an outline. This is `--strength structural`. DIPPER's order knob and an outline rebuild both change the token sequence more than a wording-only paraphrase, and they drift further from the source.

Use a rewrite model from a different family than the one that likely wrote the text. Layer A runs again on the model output, because a rewrite can reintroduce invisible characters.

One paraphrase often leaves a unigram watermark detectable (Zhao et al.; Rastogi and Pruthi, EMNLP 2024). Stealing the green list from the watermarked model and then substituting (Jovanović et al.) is not implemented: it needs a chosen-query oracle against that model, and this skill does not call one.

## Not statistical: pixel watermarks (images, audio, video)

Zhao et al. (NeurIPS 2024), *Invisible Image Watermarks Are Provably Removable Using Generative AI*, remove post-hoc pixel watermarks by adding noise and reconstructing with a denoiser or a diffusion model. The result that holds is the pair: destroy the signal, then regenerate with a generative model. A blur or a JPEG round-trip is the weaker baseline that paper beats, and it damages the picture without a way to check the watermark afterwards.

SynthID for images is not one of the schemes that paper shows are removable. This skill does not ship a generative denoiser, so it does not run that attack and does not claim those marks are gone.

## Not statistical: visible watermarks

Dekel et al. (CVPR 2017), *On the Effectiveness of Visible Watermarks*, recover the image under a semi-transparent stamp only from a collection that shares one unwarped watermark. A single image does not say which edges belong to the stamp. Inpainting the region fills it with a guess and does not invert the overlay. This skill does not remove visible watermarks.
