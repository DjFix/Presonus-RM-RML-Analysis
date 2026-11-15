#pragma once
#include "core/portable/coreparams.h"
#include <cstdint>
#include <string>
namespace presonus::panel {
// Independent initialized source-port state. Parameter is borrowed and must be
// an actual NumericParam. Name owns bounded valid NUL-terminated text. Native
// offsets +0x120/+0x118/+0xd4/+5 do not establish this structure's layout.
struct FXMainState {
  Core::Portable::NumericParam *parameter = nullptr;
  std::uint32_t mode = 0;
  std::string name;
  std::uint8_t flag = 0;
};
} // namespace presonus::panel
namespace Presonus::Panel {
// Partial source port; original return declaration, bases, layout and ARM ABI
// unresolved. Borrowed state/parameter remain live and stable through prepare.
class FXMainPage {
public:
  explicit FXMainPage(presonus::panel::FXMainState &state) : state_(state) {}
  void prepare();

private:
  presonus::panel::FXMainState &state_;
};
} // namespace Presonus::Panel
