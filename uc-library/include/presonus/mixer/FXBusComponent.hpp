#pragma once
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/OutputComponent.hpp"
#include <cstdint>
#include <vector>

#include "presonus/mixer/SendOutputComponent.hpp"
namespace Presonus::Mixer {
// Partial source-port facades. Composition is intentional: no original complete
// inheritance, field layout, ownership or unencoded return declaration claim.
class FXBusComponent {
public:
  FXBusComponent(OutputComponent &output,
                 presonus::send_output_port::SendState &state,
                 std::vector<presonus::send_output_port::SendState *> &children)
      : send_(output, state, children), state_(state), children_(children) {}
  void paramChanged(Core::Portable::Parameter *, int);

private:
  SendOutputComponent send_;
  presonus::send_output_port::SendState &state_;
  std::vector<presonus::send_output_port::SendState *> &children_;
};
} // namespace Presonus::Mixer
