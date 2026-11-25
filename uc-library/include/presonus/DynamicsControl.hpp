#pragma once

#include "core/portable/gui/corecontrols.h"
#include "core/public/coreinterpolator.h"

#include <array>

namespace Core::Portable {
class ViewController;
}

namespace Presonus {

class DynamicsControl : public Core::Portable::Control {
public:
  explicit DynamicsControl(Core::RectRef size);
  ~DynamicsControl() override;

  void draw(const Core::Portable::DrawEvent &event) override;
  void onIdle() override;
  bool onTouchInput(const Core::Portable::TouchEvent &event) override;
  void paramChanged(Core::Portable::Parameter *changed, int message) override;
  void setAttributes(const Core::Portable::Attributes &attributes) override;
  void setSize(Core::RectRef size) override;

  // Portable binding for the configuration supplied by the original page
  // factories.
  enum class Mode { Gate, Compressor };
  void configureSourcePort(Mode mode, Core::Portable::ViewController *resolver);

private:
  friend struct DynamicsControlReplay;
  void calculatePivotPoints(int &x, int &y, int &gateEnd, int &compressorEnd);

  Mode mode_ = Mode::Gate;
  Core::Portable::ViewController *resolver_ = nullptr;
  Core::Portable::BitmapReference background_;
  Core::Portable::BitmapReference handle_;
  Core::Color offLineColor_{0, 0, 0, 255};
  Core::Portable::Parameter *threshold_ = nullptr;
  Core::Portable::Parameter *ratio_ = nullptr;
  Core::Portable::Parameter *expander_ = nullptr;
  Core::LinearInterpolator vertical_;
  Core::LinearInterpolator horizontal_;
  Core::abs_time lastInvalidate_ = 0;
  std::array<int, 4> drawnPivots_{};
  bool pendingInvalidate_ = false;
};

} // namespace Presonus
