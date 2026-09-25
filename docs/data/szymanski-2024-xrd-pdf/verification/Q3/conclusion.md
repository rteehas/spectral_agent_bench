# Artifact/window tradeoff

Computed paired perturbations of 11 released Li2TiO3 patterns, each of which already contains simulated artifacts.
noise amplitude 0.03, 1-5 Å: distortion 0.0596, original-signal energy fraction 0.1059, artifact energy fraction 0.0353.
noise amplitude 0.03, 5-40 Å: distortion 0.0680, original-signal energy fraction 0.6006, artifact energy fraction 0.2914.
noise amplitude 0.03, 1-40 Å: distortion 0.0671, original-signal energy fraction 0.7065, artifact energy fraction 0.3267.
noise amplitude 0.03, 40-120 Å: distortion 0.1927, original-signal energy fraction 0.2935, artifact energy fraction 0.6733.
background amplitude 0.2, 1-5 Å: distortion 1.5348, original-signal energy fraction 0.1059, artifact energy fraction 0.9998.
background amplitude 0.2, 5-40 Å: distortion 0.0073, original-signal energy fraction 0.6006, artifact energy fraction 0.0001.
background amplitude 0.2, 1-40 Å: distortion 0.5581, original-signal energy fraction 0.7065, artifact energy fraction 1.0000.
background amplitude 0.2, 40-120 Å: distortion 0.0047, original-signal energy fraction 0.2935, artifact energy fraction 0.0000.

For these perturbations, 5–40 Å is a useful compromise: it excludes the low-r region most distorted by smooth background and avoids the greater relative noise distortion at 40–120 Å, while retaining about 60% of sampled baseline energy. That preference is conditional on the chosen noise/background amplitudes and finite angular range, and discards about 40% of baseline energy.
Window selection trades artifact suppression against retained baseline signal. The uncorrected sine transform is not a normalized physical PDF; retained energy does not establish retained classification information. Added noise uses five draws per pattern; the smooth background is deterministic. No historical robustness F1 score is implied.
