# Track 3: SimBridge — Universal DirectInput/XInput/HID Telemetry & Haptic Middleware (`simbridge`)

Zero-dependency Python reference implementation of the `SimBridge` telemetry & haptic middleware proven in `vibrant-darwin`.

## Architectural Invariants Implemented
1. **Zero Stock Game XML Tampering (`inverse_deadzone_precompensate`):**
   $$X_{\text{proxy}} = \left(d_{\text{game}} + (1 - d_{\text{game}})\sqrt{|x|}\right)\operatorname{sgn}(x)$$
2. **Loading Screen Exit Transition (`SimBridgeMiddleware`):**
   - 200 ms $C^2$ smootherstep blend ($S(t) = 6t^5 - 15t^4 + 10t^3$) when polling gap $> 1200\text{ ms}$; Frame 0 softly zeroes steering to `0`.
3. **Menu Trigger Isolation & Deadzone (`DualSenseTriggerSynthesizer`):**
   - Enforces a 15-count deadzone on L2/R2 in menus and keeps triggers in stock soft mode (`0x00`) until latched by active throttle ($R_2 > 35$) or game rumble ($>0$).
   - Synthesizes 64-byte DualSense USB HID output packets using Mode `0x21` (continuous dynamic resistance) and Mode `0x26` (oscillating ABS/slip vibration pulse).
4. **Lap & Recline Immunity (`TurnAndLeanFusion`):**
   - Projects steering rotation across the sagittal plane: $\omega_{\text{roll}} = -(\omega_z \cos\theta_{\text{pitch}} + \omega_y \sin\theta_{\text{pitch}})$.
   - Decouples lateral accelerometer gravity ($a_x$) when $|\theta_{\text{pitch}}| > 30^\circ$ so steady corner holds never decay to center.
5. **Rate-Driven Casiez 1-Euro Filter (`OneEuroFilter`):**
   - Adaptive cutoff $f_c = f_{c,\min} + \beta |\dot{x}_f|$.

## Verification
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
