#pragma once
#include "presonus/panel/control.hpp"
#include <cstdint>
namespace Presonus::Panel {
// Original RTTI: PotControl -> Control; FaderControl -> PotControl. Neither
// constructor adds stored fields. These portable declarations preserve scopes
// and encoded arguments, without claiming original layout/ordinary returns.
class PotControl : public Control {
public:
  explicit PotControl(int);
  ~PotControl() override;
  void *castTo(int) override;
  void receiveValue(int) override;
  void broadcastValue(int) override;
};
class FaderControl : public PotControl {
public:
  explicit FaderControl(int);
  ~FaderControl() override;
  void *castTo(int) override;
  void receiveValue(int) override;
  void broadcastValue(int) override;
  void handleTouch(bool);
};
} // namespace Presonus::Panel
namespace presonus::panel_binding {
// Independent provider gateway: operation0=setNormalized(raw-float,true),
// operation1=beginEdit, operation2=endEdit. Always forwards to real source CCL.
void potFaderParameterCommand(Core::Portable::Parameter &, unsigned,
                              std::uint32_t = 0);
} // namespace presonus::panel_binding
