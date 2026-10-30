#include "presonus/surface_panel/DigitalPotControl.hpp"
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {
float floating(std::uint32_t word) {
  float result;
  std::memcpy(&result, &word, sizeof result);
  return result;
}
std::uint32_t bits(float value) {
  std::uint32_t result;
  std::memcpy(&result, &value, sizeof result);
  return result;
}
using State = presonus::panel_binding::DigitalPotState;
using Endpoint = presonus::panel_binding::DigitalPotEndpoint;
struct Mutation {
  unsigned mask = 0;
  int value = 0, tag = 0, endpoint = 0;
  std::uint32_t parameter = 0;
};
struct Context {
  State *state = nullptr;
  Endpoint *endpoint = nullptr;
  Core::Portable::NumericParam *parameter = nullptr;
  Mutation base, write;
  std::vector<std::string> events;
};
std::string snapshot(const State &state) {
  return std::to_string(state.value) + ":" + std::to_string(state.tag) + ":" +
         std::to_string(state.endpoint != nullptr);
}
void mutate(Context &context, const Mutation &mutation) {
  if (mutation.mask & 1)
    context.state->value = mutation.value;
  if (mutation.mask & 2)
    context.state->tag = mutation.tag;
  if (mutation.mask & 4)
    context.state->endpoint = mutation.endpoint ? context.endpoint : nullptr;
}
void baseChanged(void *opaque, Core::Portable::Parameter *parameter, int mode) {
  auto &context = *static_cast<Context *>(opaque);
  const auto before = snapshot(*context.state);
  mutate(context, context.base);
  if (context.base.mask & 8)
    parameter->setValue(floating(context.base.parameter), false);
  context.events.push_back("B:" + std::to_string(mode) + ":" +
                           std::to_string(parameter != nullptr) + ":" + before +
                           ":" + snapshot(*context.state) + ":" +
                           std::to_string(bits(context.parameter->getValue())));
}
void writePrefix(void *opaque, const std::array<std::uint8_t, 3> &prefix) {
  auto &context = *static_cast<Context *>(opaque);
  const auto before = snapshot(*context.state);
  mutate(context, context.write);
  context.events.push_back("W:" + std::to_string(prefix[0]) + ":" +
                           std::to_string(prefix[1]) + ":" +
                           std::to_string(prefix[2]) + ":" + before + ":" +
                           snapshot(*context.state));
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 1;
  std::ifstream input(argv[1]);
  if (!input)
    return 2;
  unsigned cases = 0;
  char operation;
  int initialValue, tag, hasEndpoint, argument, mode, hasParameter;
  std::uint32_t parameterBits;
  while (input >> operation >> initialValue >> tag >> hasEndpoint >> argument >>
         mode >> hasParameter >> parameterBits) {
    Context context;
    if (!(input >> context.base.mask >> context.base.value >>
          context.base.tag >> context.base.endpoint >> context.base.parameter >>
          context.write.mask >> context.write.value >> context.write.tag >>
          context.write.endpoint))
      return 3;
    int expectedValue, expectedTag, expectedEndpoint;
    std::uint32_t expectedParameter;
    unsigned eventCount;
    if (!(input >> expectedValue >> expectedTag >> expectedEndpoint >>
          expectedParameter >> eventCount))
      return 4;
    std::vector<std::string> events(eventCount);
    for (auto &event : events)
      if (!(input >> event))
        return 5;
    const Core::Portable::ParamInfo info = PARAM_FLOAT(
        1, "digital-pot", floating(0xff800000U), floating(0x7f800000U),
        floating(parameterBits), 0.1F, nullptr, nullptr, 0.0F, 0);
    Core::Portable::NumericParam parameter(info);
    State state;
    Endpoint endpoint{&context, writePrefix};
    context.state = &state;
    context.endpoint = &endpoint;
    context.parameter = &parameter;
    state.value = initialValue;
    state.tag = tag;
    state.endpoint = hasEndpoint ? &endpoint : nullptr;
    state.context = &context;
    state.baseParamChanged = baseChanged;
    Presonus::Panel::DigitalPotControl control(state);
    if (operation == 'T')
      control.transmit();
    else if (operation == 'B')
      control.broadcastValue(argument);
    else if (operation == 'P')
      control.paramChanged(hasParameter ? &parameter : nullptr, mode);
    else
      return 6;
    if (state.value != expectedValue || state.tag != expectedTag ||
        (state.endpoint != nullptr) != (expectedEndpoint != 0) ||
        bits(parameter.getValue()) != expectedParameter ||
        context.events != events) {
      std::cerr << "Mismatch case " << cases << " op " << operation << '\n';
      return 7;
    }
    ++cases;
  }
  if (!input.eof() || !cases)
    return 8;
  std::cout << "PASS " << cases
            << " original ARM DigitalPot state/prefix/base-call cases with "
               "actual CCL NumericParam\n";
}
