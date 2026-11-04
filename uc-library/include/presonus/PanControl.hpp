#pragma once
#include "core/portable/gui/corecontrols.h"
#include "core/portable/gui/coreviewcontroller.h"
#include <array>
#include <functional>

namespace Presonus {
// Portable source port. Fields, inheritance and return declarations below are
// source-port choices, not recovered ARM layout or original header
// declarations.
class PanControl : public Core::Portable::ValueBar {
public:
  using Parameter = Core::Portable::Parameter;
  // Independent app adapter for the unresolved original channel/group lookup.
  using ChannelSideResolver =
      std::function<bool(Core::Portable::IParamObserver *)>;
  PanControl() = default;
  PanControl(const Core::Rect &rect, Parameter *parameter);
  void setAttributes(const Core::Portable::Attributes &) override;
  void bindPanController(Core::Portable::ViewController *p) {
    panController_ = p;
  }
  int panValueBarWidth() const { return valueBarWidth_; }
  void setStereoParam(Parameter *parameter);
  void setLinkParam(Parameter *parameter);
  void setChannelNumberParam(Parameter *parameter);
  void setRightSideParam(Parameter *parameter);
  void setStereoPanParam(Parameter *parameter);
  bool isStereo() const;
  bool isLinked() const;
  float computeLinkedPanValue(float value) const;
  bool isRightSideOfLink() const;
  void paramChanged(Parameter *p, int msg) override;
  // Non-owning, independent source-port binding API. Order follows observed
  // native lookup precedence, not native object layout.
  void bindPanParameters(const std::array<Parameter *, 5> &parameters);
  const std::array<Parameter *, 5> &panParameters() const;
  void setChannelSideResolver(ChannelSideResolver resolver);

private:
  std::array<Parameter *, 5>
      parameters_{}; // stereo, link, label, side, auxiliary
  ChannelSideResolver channelSideResolver_;
  Core::Portable::ViewController *panController_ = nullptr;
  int valueBarWidth_ = 0;
};
} // namespace Presonus
