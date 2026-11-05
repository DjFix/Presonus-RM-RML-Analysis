#pragma once
#include "core/portable/coreparams.h"
#include "core/portable/gui/corecontrols.h"
#include "core/portable/gui/coregraphics.h"
#include "core/portable/gui/coreview.h"
#include "core/public/coreinterpolator.h"
#include "core/public/corevector.h"
#include <cstdint>
#include <memory>
#include <vector>
namespace presonus::dsp {
// Independent partial-object construction; not an original constructor.
struct EQControlBiquadPortTag {};
} // namespace presonus::dsp
namespace Presonus {
class BackgroundPainter;
class EQControl;
} // namespace Presonus
namespace presonus::dsp {
// Explicit app integration boundary. A real renderer/provider must supply both
// operations; EQControl never silently substitutes an empty callback.
struct EQControlDrawBoundary {
  virtual ~EQControlDrawBoundary() = default;
  virtual void releaseBuffer() = 0;
  virtual void initBands(Presonus::EQControl &) = 0;
};
} // namespace presonus::dsp
namespace Presonus {
// Intentional portable source port. Original GUI inheritance, layout,
// virtual table and lifecycle are not represented by this portable class.
class EQControl {
public:
  explicit EQControl(presonus::dsp::EQControlBiquadPortTag) : observer(*this) {}
  // Original ordinary return declaration is unresolved; int is provisional.
  // Supported equivalence domain: index >= 0. Original negative indexing is
  // unchecked and deliberately receives no supported behavior claim.
  int getBiquadType(int index) const;
  // Intentional portable state; these are not original fields or ARM layout.
  struct PortableBand {
    bool on = false;
    bool enabled = false;
    std::uint8_t dirty = 0;
    float frequency = 0.f;
    float gain = 0.f;
    int x = 0, y = 0;
    bool forceCurve = false;
  };
  // Six pointer slots are independently observed. Names and portable host
  // layout are source-port choices, not original field/ARM-layout claims.
  struct BandParams {
    Core::Portable::Parameter *gain = nullptr;
    Core::Portable::Parameter *q = nullptr;
    Core::Portable::Parameter *frequency = nullptr;
    // Original six slots are observed, their field names remain unresolved.
    Core::Portable::Parameter *slot3 = nullptr, *slot4 = nullptr,
                              *slot5 = nullptr;
    bool contains(Core::Portable::Parameter *parameter) const;
    void zeroParam(Core::Portable::Parameter *parameter);
  };
  // Compatibility name for the SAME coherent binding, not a second model.
  using PortableBandParams = BandParams;
  std::vector<PortableBand> &portableBandState() { return portableBands; }
  const std::vector<PortableBand> &portableBandState() const {
    return portableBands;
  }
  // Ordinary return declarations provisional; independently observed side
  // effects and boolean result are covered by the bounded native replay.
  std::vector<PortableBandParams> &portableParameterState() {
    return portableParams;
  }
  void markBandDirty(int index);
  int parseType(Core::ConstString name);
  float getFrequency(int index) const;
  float getGain(int index) const;
  float getQ(int index) const;
  void addBackgroundPainter(BackgroundPainter &painter);
  Core::Vector<BackgroundPainter *> &portableBackgroundPainters() {
    return backgroundPainters;
  }
  void bindPortableInterpolators(const Core::Interpolator &frequency,
                                 const Core::LinearInterpolator &x,
                                 const Core::LinearInterpolator &gain,
                                 const Core::LinearInterpolator &y) {
    frequencyNormalizer = &frequency;
    xPixels = &x;
    gainNormalizer = &gain;
    yPixels = &y;
  }
  int freqToX(float frequency) const;
  int toXGridPixel(float frequency) const;
  int toYGridPixel(float gain) const;
  // Provisional ordinary returns. Type is explicitly bound independently of
  // gain: native type slot0, gain slot1, Q slot2, frequency slot3 are observed
  // by separate getter ranges. Legacy BandParams clearing is unchanged.
  int getType(int index) const;
  bool getBandEnabled(int index) const;
  void bindPortableTypeParameters(
      const std::vector<Core::Portable::Parameter *> &parameters) {
    typeParameters = parameters;
  }
  void bindPortableView(Core::Portable::View &view) { portableView = &view; }
  void bindPortablePrimaryParameter(Core::Portable::Parameter *parameter) {
    primaryParameter = parameter;
  }
  int getBandForPoint(const Core::TPoint<int> &point) const;
  bool onTouchInput(const Core::Portable::TouchEvent &event);
  // Source-port storage and actual CCL rendering; native array/object layout
  // and allocator failure/exception behavior are not reproduced.
  void initBands();
  // Provisional ordinary returns; these are portable source interfaces, not
  // recovered original declarations or GUI/ARM object layout.
  void setNumBands(int count);
  void setSize(const Core::TRect<int> &rectangle);
  bool getCurve(float *destination, int index, int samples) const;
  void rebuildCurves();
  void onIdle();
  void bindPortableCurveRange(float minimum, float maximum) {
    curveMinimum = minimum;
    curveMaximum = maximum;
  }
  // Explicit portable clock state for restoration and deterministic replay.
  std::int64_t &portableLastCurveTime() { return lastCurveTime; }
  int portableRequestedBandCount() const { return requestedBandCount; }

  // Explicit source-port observer adapter, not original GUI inheritance.
  void bindPortableControl(Core::Portable::Control &control) {
    observerControl = &control;
  }
  Core::Portable::IParamObserver *portableObserver() { return &observer; }
  void paramChanged(Core::Portable::Parameter *parameter, int message);
  void drawCurve(const Core::Portable::DrawEvent &event,
                 const Core::Color &color, bool mode);
  std::vector<float> &portableAmplitudeCurve() { return amplitudeCurve; }
  std::vector<int> &portablePixelCurve() { return pixelCurve; }
  std::vector<std::vector<float>> &portableBandCurveStorage() {
    return bandCurves;
  }
  const std::vector<std::vector<float>> &portableBandCurves() const {
    return bandCurves;
  }
  const Core::Portable::Bitmap *portableBitmap() const { return bitmap.get(); }
  int gainToY(float gain) const;
  bool isAnyBandOn() const;
  void
  bindPortableDrawBoundary(presonus::dsp::EQControlDrawBoundary &boundary) {
    drawBoundary = &boundary;
  }
  void setPortableBufferState(bool present, bool valid) {
    bufferPresent = present;
    bufferValid = valid;
  }
  bool portableBufferedDraw() const { return bufferedDraw; }
  // Provisional bool source return; native byte observations cover 0 and 1.
  bool isBufferedDraw() const;
  bool portableBufferPresent() const { return bufferPresent; }
  bool portableBufferValid() const { return bufferValid; }
  void setBufferedDraw(bool state);

private:
  // Source-port borrowed bindings, not original fields or inheritance.
  struct Observer : Core::Portable::ParamObserverBase {
    EQControl &owner;
    explicit Observer(EQControl &owner) : owner(owner) {}
    void paramChanged(Core::Portable::Parameter *p, int message) override {
      owner.paramChanged(p, message);
    }
  } observer;
  Core::Portable::Control *observerControl = nullptr;
  std::vector<std::vector<float>> bandCurves;
  std::vector<float> amplitudeCurve;
  std::vector<int> pixelCurve;
  std::unique_ptr<Core::Portable::Bitmap> bitmap;
  Core::Portable::View *portableView = nullptr;
  Core::Portable::Parameter *primaryParameter = nullptr;
  std::vector<Core::Portable::Parameter *> typeParameters;
  struct SortedBand {
    int index = 0, x = 0, left = -1, right = -1;
  };
  std::vector<PortableBand> portableBands;
  std::vector<PortableBandParams> portableParams;
  Core::Vector<BackgroundPainter *> backgroundPainters;
  const Core::Interpolator *frequencyNormalizer = nullptr;
  const Core::LinearInterpolator *xPixels = nullptr;
  const Core::LinearInterpolator *gainNormalizer = nullptr;
  const Core::LinearInterpolator *yPixels = nullptr;
  presonus::dsp::EQControlDrawBoundary *drawBoundary = nullptr;
  int requestedBandCount = 0;
  float curveMinimum = 20.f, curveMaximum = 20000.f;
  std::int64_t lastCurveTime = 0;
  bool bufferedDraw = false;
  bool bufferPresent = false;
  bool bufferValid = false;
};
} // namespace Presonus
