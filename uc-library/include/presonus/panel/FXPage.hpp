#pragma once
#include "core/portable/coreparams.h"
#include <cstdint>
namespace Presonus::Panel {
// Independent source-port state; the native offsets are evidence, not this
// layout. The live actual CCL parameter is borrowed, with no ownership
// transfer.
struct FXPageState {
  Core::Portable::NumericParam *parameter;
  float lower;
  float upper;
  std::uint8_t inRange;
};
// Partial port: no original constructor, base, field layout or ARM ABI claim.
class FXPage {
public:
  explicit FXPage(FXPageState &state) : state(state) {}
  // Ordinary original return declaration remains unresolved.
  void prepare();

private:
  FXPageState &state;
};
} // namespace Presonus::Panel
