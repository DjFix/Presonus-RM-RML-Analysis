#include "presonus/mixer/SendOutputComponent.hpp"

#include <array>
#include <cassert>
#include <cstdlib>
#include <iostream>

int main(int argc, char **argv) {
  Core::Portable::ParamInfo info{};
  info.tag = 14;
  Core::Portable::NumericParam parameter(info);
  using presonus::send_output_port::SendState;
  std::array<presonus::mixer::ChannelState, 2> channels{};
  std::array<presonus::output_port::Bindings, 2> bindings{
      {{channels[0]}, {channels[1]}}};
  std::array<SendState, 2> states{{{bindings[0]}, {bindings[1]}}};
  std::vector<SendState *> children{&states[1]};
  Presonus::Mixer::OutputComponent firstBase(bindings[0]),
      secondBase(bindings[1]);
  Presonus::Mixer::SendOutputComponent first(firstBase, states[0], children),
      second(secondBase, states[1], children);
  std::array receivers{&first, &second};
  for (auto &state : states) {
    state.sendChanged = 91;
    state.childChanged = 92;
    state.fxChanged = 93;
  }
  for (int caseIndex = 1; caseIndex < argc; ++caseIndex) {
    const auto index = ((caseIndex - 1) / 6) % 2;
    states[index].auxPreModeWord = std::strtoul(argv[caseIndex], nullptr, 0);
    const auto otherWord = states[1 - index].auxPreModeWord;
    std::cout << receivers[index]->getAuxPreMode() << '\n';
    assert(receivers[1 - index]->getAuxPreMode() == otherWord);
    for (const auto &state : states) {
      assert(state.sendChanged == 91 && state.childChanged == 92 &&
             state.fxChanged == 93 && !state.output.updatePending);
    }
  }
  int delegated = 0;
  bindings[0].channelParamChanged = [&](auto *param, int message) {
    assert(param == &parameter && message == 3);
    ++delegated;
  };
  const auto firstWord = first.getAuxPreMode();
  const auto secondWord = second.getAuxPreMode();
  first.paramChanged(&parameter, 3);
  assert(delegated == 1);
  for (const auto &binding : bindings)
    assert(binding.updatePending && binding.outputCoeffChanged == 1);
  assert(first.getAuxPreMode() == firstWord &&
         second.getAuxPreMode() == secondWord);
}
