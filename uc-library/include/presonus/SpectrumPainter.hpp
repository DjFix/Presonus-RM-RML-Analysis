#pragma once

#include "core/public/corevector.h"
#include "presonus/BackgroundPainter.hpp"
#include "presonus/IBackgroundGridProvider.hpp"

namespace Presonus {

class SpectrumPainter : public BackgroundPainter {
public:
  explicit SpectrumPainter(IBackgroundGridProvider &grid);
  // Independent source-port view of a caller-owned rectangle.
  explicit SpectrumPainter(const Core::TRect<int> &last)
      : borrowedLast_(&last) {}

  void setData(const float *amplitudes, int count, const float *frequencies);
  void init(const Core::TRect<int> &bounds);
  Core::TRect<int> calculateBars(const Core::TRect<int> &bounds);
  Core::TRect<int> calculateNextDrawRect(const Core::TRect<int> &bounds);
  void paint(const Core::TRect<int> &bounds,
             const Core::Portable::DrawEvent &event,
             const Core::Portable::Style &style) override;
  Core::TRect<int> getLastDrawnRect() const;

private:
  struct Bar {
    float previousAmplitude = 0.f;
    float decibels = 0.f;
    int center = 0;
    Core::TRect<int> rect;
  };

  IBackgroundGridProvider *grid_ = nullptr;
  const float *amplitudes_ = nullptr;
  const float *frequencies_ = nullptr;
  int count_ = 0;
  bool initialized_ = false;
  Core::Vector<Bar> bars_;
  Core::TRect<int> last_;
  Core::TRect<int> next_;
  const Core::TRect<int> *borrowedLast_ = nullptr;
};

} // namespace Presonus
