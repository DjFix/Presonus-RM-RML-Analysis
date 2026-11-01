#include "presonus/dsp/Controller.hpp"
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <vector>
namespace {
float number(std::uint32_t word) {
  float value;
  std::memcpy(&value, &word, sizeof value);
  return value;
}
std::uint32_t word(float value) {
  std::uint32_t bits;
  std::memcpy(&bits, &value, sizeof bits);
  return bits;
}
struct Event {
  int call, tag;
  std::uint32_t value;
};
struct Curve : Core::Interpolator {
  explicit Curve(float low, float high, std::vector<Event> &events)
      : Core::Interpolator(low, high), events(events) {}
  float normalizedToRange(float value) const override {
    events.push_back({4, 0, word(value)});
    return .75f;
  }
  float rangeToNormalized(float value) const override {
    events.push_back({5, 0, word(value)});
    return .75f;
  }
  std::vector<Event> &events;
};
struct Controller : Presonus::Dsp::Controller {
  explicit Controller(std::vector<Event> &events, bool hooks)
      : Presonus::Dsp::Controller(presonus::dsp::ControllerSourceTag{}),
        events(events), hooks(hooks) {}
  float getValue(int tag) const override {
    events.push_back({1, tag, 0});
    return .75f;
  }
  float setValue(int tag, float value) override {
    events.push_back({0, tag, word(value)});
    return .5f;
  }
  float normalizedValueToRange(int tag, float value) const override {
    if (!hooks)
      return Presonus::Dsp::Controller::normalizedValueToRange(tag, value);
    events.push_back({2, tag, word(value)});
    return .75f;
  }
  float rangeToNormalizedValue(int tag, float value) const override {
    if (!hooks)
      return Presonus::Dsp::Controller::rangeToNormalizedValue(tag, value);
    events.push_back({3, tag, word(value)});
    return .5f;
  }
  std::vector<Event> &events;
  bool hooks;
};
} // namespace
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  if (!input)
    return 3;
  int method, mode, index, converter, guard;
  std::uint32_t value, low, high;
  while (input >> method >> mode >> index >> converter >> value >> low >>
         high >> guard) {
    std::vector<Event> events;
    Controller controller(events, method <= 2);
    std::vector<std::unique_ptr<Presonus::Dsp::ParamDescriptor>> owned;
    Presonus::Dsp::ParamDescriptor *items[3];
    for (int i = 0; i < 3; ++i) {
      owned.push_back(std::make_unique<Presonus::Dsp::ParamDescriptor>(
          presonus::dsp::DescriptorSourceTag{}));
      items[i] = owned.back().get();
      items[i]->sourceState().tag = 10 + 10 * i;
      if (converter)
        items[i]->sourceState().interpolator =
            new Curve(number(low), number(high), events);
    }
    if (mode == 4 && index >= 0 && index < 3)
      items[index] = nullptr;
    Core::ConstVector<Presonus::Dsp::ParamDescriptor *> descriptors(
        items, mode == 6 ? 0 : 3);
    auto &error =
        Core::ConstVector<Presonus::Dsp::ParamDescriptor *>::getError();
    auto *previous = error;
    error = mode == 5 ? items[0] : nullptr;
    controller.sourceState().descriptors = mode == 0 ? nullptr : &descriptors;
    controller.sourceState().lookupByTag =
        mode == 2 || mode == 3 || mode == 6 || mode == 7;
    float result;
    switch (method) {
    case 1:
      result = controller.getNormalized(index);
      break;
    case 2:
      result = controller.setNormalized(index, number(value));
      break;
    case 3:
      result = controller.normalizedValueToRange(index, number(value));
      break;
    case 4:
      result = controller.rangeToNormalizedValue(index, number(value));
      break;
    case 5:
      result = controller.boundValue(index, number(value));
      break;
    default:
      return 4;
    }
    error = previous;
    std::cout << word(result) << ' ' << events.size();
    for (const auto &event : events)
      std::cout << ' ' << event.call << ' ' << event.tag << ' ' << event.value;
    std::cout << '\n';
  }
  return input.eof() ? 0 : 5;
}
