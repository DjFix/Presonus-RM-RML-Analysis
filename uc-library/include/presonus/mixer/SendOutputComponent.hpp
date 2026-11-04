#pragma once
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/OutputComponent.hpp"
#include <cstdint>
#include <vector>

namespace presonus::send_output_port {
// Independent portable state, named by observed native stores, not ARM fields.
struct SendState {
  presonus::output_port::Bindings &output;
  std::uint32_t sendChanged{};  // observed native +0x178
  std::uint32_t childChanged{}; // observed native +0x18c
  std::uint32_t fxChanged{};    // independent state for native +0x194
};
} // namespace presonus::send_output_port

namespace Presonus::Mixer {
// Partial source-port facades. Composition is intentional: no original complete
// inheritance, field layout, ownership or unencoded return declaration claim.
class SendOutputComponent {
public:
  SendOutputComponent(
      OutputComponent &base, presonus::send_output_port::SendState &state,
      std::vector<presonus::send_output_port::SendState *> &children)
      : base_(base), state_(state), children_(children) {}
  void paramChanged(Core::Portable::Parameter *, int);

private:
  OutputComponent &base_;
  presonus::send_output_port::SendState &state_;
  std::vector<presonus::send_output_port::SendState *> &children_;
};
} // namespace Presonus::Mixer
