#pragma once
#include "core/portable/coreparams.h"
#include "core/portable/gui/corebitmap.h"
#include "core/portable/gui/corecontrols.h"
#include "core/portable/gui/coregraphics.h"
#include "core/portable/gui/coreview.h"
#include "core/portable/gui/coreviewcontroller.h"
#include "core/public/coreinterpolator.h"
#include "core/public/corevector.h"
#include "presonus/IBackgroundGridProvider.hpp"
#include "presonus/mixer_dsp/EqSourceProviders.hpp"
#include <array>
#include <cstdint>
#include <memory>
#include <vector>
namespace presonus::dsp {
// Independent app-side provider adaptation. Pinned CCL 5.0.0 has no
// Core::LogInterpolator. The observed (0,1) bootstrap stores real CCL range
// state but cannot convert until setRange selects an existing supported
// positive EQ domain. A failed range transition leaves the last range values
// visible but disables conversion until a supported setRange succeeds. Reset to
// (0,1) disables conversion. This is not legacy Core conversion or ARM
// behavior.
class EQControlFrequencyInterpolator final : public Core::Interpolator {
public:
  EQControlFrequencyInterpolator();
  void setRange(float minimum, float maximum, float midpoint = 0.f) override;
  float normalizedToRange(float value) const override;
  float rangeToNormalized(float value) const override;
  bool sourceRangeSupported() const { return configured; }
  // Source-port setup stores arbitrary native display bounds; conversion stays
  // restricted to the independently validated positive provider domains.
  void setDisplayRange(float minimum, float maximum);

private:
  EqLogSourceInterpolator positiveRange;
  bool configured = false;
};
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
// virtual table and ARM lifecycle ABI are not represented by this portable
// class.
class EQControl : public IBackgroundGridProvider {
public:
  explicit EQControl(presonus::dsp::EQControlBiquadPortTag) : observer(*this) {}
  // Original encoded constructor interface; composition below is a portable
  // source model, not recovered GUI inheritance or original ARM object layout.
  explicit EQControl(const Core::TRect<int> &rectangle);
  virtual ~EQControl();
  struct PortableConstructorState {
    explicit PortableConstructorState(const Core::Rect &rectangle);
    // Destruction order: parameters before interpolators before the control.
    // This RAII support establishes no original destructor readiness.
    Core::Portable::Control control;
    Core::LinearInterpolator gain{0.f, 1.f}, y{0.f, 1.f};
    presonus::dsp::EQControlFrequencyInterpolator frequency;
    Core::LinearInterpolator x{0.f, 1.f};
    const Core::Portable::ParamInfo *const hpfInfo;
    // Separate ownership permits native-phase ParamList cleanup while the
    // observer and Control are still alive. The reference is valid until
    // EQControl destruction begins; it is not an original object field.
    std::unique_ptr<Core::Portable::ParamList> hpfParameterOwner;
    Core::Portable::ParamList &hpfParameters;
    int handleDiameter = 10;
    Core::Color offlineColor{0, 0, 0, 255};
    // Explicit null borrowed source-port boundaries. Original declarations of
    // these three native slots remain unresolved; no layout/type claim.
    std::array<const void *, 3> borrowedBindings{};
  };
  const PortableConstructorState *portableConstructorState() const {
    return constructorState.get();
  }
  // Explicit borrowed source-port injection, not recovery of the original
  // writer to native this+0x5c. The real controller must outlive setup.
  void bindPortableViewController(Core::Portable::ViewController &controller) {
    viewController = &controller;
  }
  // Original ordinary return declaration remains unresolved; void provisional.
  // Requires the rectangle constructor's owned providers and a real controller.
  void setAttributes(const Core::Portable::Attributes &attributes);
  const Core::Portable::Bitmap *portableBandImage(unsigned index) const {
    return index < bandImages.size() ? bandImages[index].getBitmap() : nullptr;
  }
  const Core::Portable::Bitmap *portableDefaultImage() const {
    return defaultBitmap.getBitmap();
  }
  const Core::Portable::Bitmap *portableBackgroundImage() const {
    return backgroundBitmap.getBitmap();
  }
  float portableCurveMinimum() const { return curveMinimum; }
  float portableCurveMaximum() const { return curveMaximum; }
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
    // Observer/setBand semantic mapping: native slots 0..5 map to
    // slot3 (type), gain, q, frequency, slot4 (enabled), slot5.
    // Legacy contains/zeroParam retain their positional compatibility behavior.
    // This mapping is a source-port conversion, never an ARM object layout.
    // Ordinary void return declarations remain provisional.
    void addObserver(EQControl *owner);
    void removeObserver(EQControl *owner);
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
  // Requires parameter/type/curve bindings covering portableBands. Borrowed
  // parameters outlive the synchronous operation; no concurrent/reentrant
  // resize. Original ordinary return declaration unresolved; void is
  // provisional.
  void setBand(int index, BandParams parameters);
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
  int toXGridPixel(float frequency) const override;
  int toYGridPixel(float gain) const override;
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
  // Original ordinary return declaration is unresolved; void is provisional.
  // Rendering uses actual CCL providers with portable state, not ARM layout.
  void draw(const Core::Portable::DrawEvent &event);
  void bindPortableHandleStyle(int diameter, const Core::Color &offline) {
    portableHandleDiameter = diameter;
    portableOfflineColor = offline;
  }
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
  // Source-port lifetime bindings: shared images are referenced, never owned.
  // Borrowed images and parameters must outlive this object. Array cookies,
  // original fields and ARM layout are deliberately not represented.
  void
  bindPortableBandImages(const std::vector<Core::Portable::Bitmap *> &images) {
    bandImages.resize(images.size());
    for (unsigned i = 0; i < images.size(); ++i)
      bandImages[i] = images[i];
  }
  void bindPortableImages(Core::Portable::Bitmap *defaultImage,
                          Core::Portable::Bitmap *backgroundImage) {
    defaultBitmap = defaultImage;
    backgroundBitmap = backgroundImage;
  }
  void bindPortableOwnedBitmap(std::unique_ptr<Core::Portable::Bitmap> value) {
    bitmap = std::move(value);
  }
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
  // Owned composition only for the rectangle constructor. The tagged partial
  // object retains its existing borrowed-provider behavior and defaults.
  std::unique_ptr<PortableConstructorState> constructorState;
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
  std::vector<Core::Portable::BitmapReference> bandImages;
  Core::Portable::BitmapReference defaultBitmap, backgroundBitmap;
  Core::Portable::ViewController *viewController = nullptr;
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
  int portableHandleDiameter = 10;
  Core::Color portableOfflineColor{0, 0, 0, 255};
  int requestedBandCount = 0;
  float curveMinimum = 20.f, curveMaximum = 20000.f;
  float displayMinimumLevel = 0.f, displayMaximumLevel = 0.f;
  std::int64_t lastCurveTime = 0;
  bool bufferedDraw = false;
  bool bufferPresent = false;
  bool bufferValid = false;
};
} // namespace Presonus
