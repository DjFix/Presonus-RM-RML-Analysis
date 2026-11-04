#pragma once
#include "core/portable/coreparams.h"
#include "core/public/coreinterpolator.h"
#include "core/public/corevector.h"
#include <cstdint>
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
  explicit EQControl(presonus::dsp::EQControlBiquadPortTag) {}
  // Original ordinary return declaration is unresolved; int is provisional.
  // Supported equivalence domain: index >= 0. Original negative indexing is
  // unchecked and deliberately receives no supported behavior claim.
  int getBiquadType(int index) const;
  // Intentional portable state; these are not original fields or ARM layout.
  struct PortableBand {
    bool on = false;
    bool enabled = false;
    std::uint8_t dirty = 0;
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
  std::vector<PortableBand> portableBands;
  std::vector<PortableBandParams> portableParams;
  Core::Vector<BackgroundPainter *> backgroundPainters;
  const Core::Interpolator *frequencyNormalizer = nullptr;
  const Core::LinearInterpolator *xPixels = nullptr;
  const Core::LinearInterpolator *gainNormalizer = nullptr;
  const Core::LinearInterpolator *yPixels = nullptr;
  presonus::dsp::EQControlDrawBoundary *drawBoundary = nullptr;
  bool bufferedDraw = false;
  bool bufferPresent = false;
  bool bufferValid = false;
};
} // namespace Presonus
