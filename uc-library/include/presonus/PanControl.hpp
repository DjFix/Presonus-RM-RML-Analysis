#pragma once
#include "core/portable/gui/corecontrols.h"
#include <array>
#include <functional>

namespace Presonus {
// Portable source port. Fields, inheritance and return declarations below are
// source-port choices, not recovered ARM layout or original header
// declarations.
class PanControl : public Core::Portable::Control {
public:
  using Parameter = Core::Portable::Parameter;
  // Independent app adapter for the unresolved original channel/group lookup.
  using ChannelSideResolver =
      std::function<bool(Core::Portable::IParamObserver *)>;
  PanControl() = default;
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
};
} // namespace Presonus
