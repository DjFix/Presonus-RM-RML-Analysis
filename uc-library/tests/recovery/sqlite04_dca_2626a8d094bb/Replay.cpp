#include "presonus/mixer/DCALevelHandler.hpp"

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>

using Core::Portable::NumericParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Presonus::Mixer::DCALevelHandler;

static uint32_t bits(float value) {
  uint32_t word;
  std::memcpy(&word, &value, sizeof(word));
  return word;
}

static float input(const char *text) {
  const auto word = static_cast<uint32_t>(std::stoul(text));
  float value;
  std::memcpy(&value, &word, sizeof(value));
  return value;
}

class TraceParameter final : public NumericParam {
public:
  explicit TraceParameter(const ParamInfo &info) : NumericParam(info) {}

  float getMin() const override {
    const auto minimum = NumericParam::getMin();
    std::cout << "min " << bits(minimum) << '\n';
    return minimum;
  }

  float getValue() const override {
    const auto value = NumericParam::getValue();
    std::cout << "get " << bits(value) << '\n';
    return value;
  }

  void setValue(float value, bool edit) override {
    std::cout << "set " << bits(value) << ' ' << edit << '\n';
    NumericParam::setValue(value, edit);
  }
};

class Observer final : public Core::Portable::ParamObserverBase {
public:
  void paramChanged(Parameter *, int message) override {
    std::cout << "observe " << message << '\n';
  }
};

extern float invokeGet(DCALevelHandler *, Parameter *) asm(
    "_ZN8Presonus5Mixer15DCALevelHandler10getDBValueEPN4"
    "Core8Portable9ParameterE");
extern void invokeSet(DCALevelHandler *, Parameter *,
                      float) asm("_ZN8Presonus5Mixer15DCALevelHandler10setDBVal"
                                 "ueEPN4Core8Portable9ParameterEf");

int main(int argc, char **argv) {
  if (argc != 5)
    return EXIT_FAILURE;

  const std::string mode(argv[1]);
  const float minimum = input(argv[2]);
  const float value = input(argv[3]);
  const float proposed = input(argv[4]);
  const ParamInfo info{ParamInfo::kFloat, 0, "level", -10000.f, 10000.f};
  auto targetInfo = info;
  targetInfo.minValue = minimum;
  NumericParam level(info);
  NumericParam trim(info);
  DCALevelHandler handler(&level, &trim, 0);
  TraceParameter target(targetInfo);
  target.setValueFast(value);
  Observer observer;
  target.setController(&observer);
  target.addObserver(&observer);

  if (mode == "provider-get") {
    target.getMin();
    target.getValue();
  } else if (mode == "provider-set") {
    target.setValue(proposed, true);
    const auto result = target.getValue();
    std::cout << "final " << bits(result) << '\n';
  } else if (mode == "get") {
    const auto result = invokeGet(&handler, &target);
    std::cout << "return " << bits(result) << '\n';
  } else if (mode == "set") {
    invokeSet(&handler, &target, proposed);
    const auto result = target.getValue();
    std::cout << "final " << bits(result) << '\n';
  } else {
    return EXIT_FAILURE;
  }
  target.removeObserver(&observer);
  target.setController(nullptr);
}
