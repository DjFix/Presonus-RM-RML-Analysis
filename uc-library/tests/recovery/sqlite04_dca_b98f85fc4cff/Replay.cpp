#include "presonus/mixer/DCALevelHandler.hpp"
#include "presonus/mixer/FilterGroupComponent.hpp"

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

using namespace Core::Portable;
using Presonus::Mixer::DCALevelHandler;
using Presonus::Mixer::FilterGroupComponent;

namespace {
bool tracing = false;

uint32_t bits(float value) {
  uint32_t word;
  std::memcpy(&word, &value, sizeof(word));
  return word;
}

float fromBits(const char *text) {
  auto word = static_cast<uint32_t>(std::stoul(text));
  float value;
  std::memcpy(&value, &word, sizeof(value));
  return value;
}

class Observer final : public ParamObserverBase {
public:
  explicit Observer(const char *label) : label_(label) {}

  void paramChanged(Parameter *, int message) override {
    if (tracing)
      std::cout << "observe " << label_ << ' ' << message << '\n';
  }

private:
  const char *label_;
};

class TraceParam final : public NumericParam {
public:
  TraceParam(const ParamInfo &info, std::string label)
      : NumericParam(info), label_(std::move(label)) {}

  float getMin() const override {
    const auto value = NumericParam::getMin();
    if (tracing)
      std::cout << "min " << label_ << ' ' << bits(value) << '\n';
    return value;
  }

  float getValue() const override {
    const auto value = NumericParam::getValue();
    if (tracing)
      std::cout << "get " << label_ << ' ' << bits(value) << '\n';
    return value;
  }

  void setValue(float value, bool edit) override {
    if (tracing)
      std::cout << "set " << label_ << ' ' << bits(value) << ' ' << edit
                << '\n';
    NumericParam::setValue(value, edit);
  }

private:
  std::string label_;
};
} // namespace

int main(int argc, char **argv) {
  if (argc < 9)
    return EXIT_FAILURE;
  std::string mode(argv[1]);
  ParamInfo levelInfo{ParamInfo::kFloat, 0, "level", fromBits(argv[2]),
                      10000.f};
  levelInfo.flags = std::stoi(argv[5]);
  const ParamInfo trimInfo{ParamInfo::kFloat, 0, "trim", -10000.f, 10000.f};
  const int action = std::stoi(argv[6]);
  const int tag = std::stoi(argv[7]);
  const bool alias = std::stoi(argv[8]) != 0;
  TraceParam level(levelInfo, "L");
  TraceParam trim(trimInfo, "T");
  auto *trimParam = alias ? &level : &trim;
  level.setValueFast(fromBits(argv[3]));
  trim.setValueFast(fromBits(argv[4]));
  const float originalTrim = trimParam->getValue();
  Observer levelObserver("L");
  Observer trimObserver("T");
  level.setController(&levelObserver);
  level.addObserver(&levelObserver);
  trim.setController(&trimObserver);
  trim.addObserver(&trimObserver);

  tracing = mode == "ctor";
  auto handler = std::make_unique<DCALevelHandler>(&level, trimParam, tag);
  tracing = false;
  // Preserve the requested trim starting state independently of constructor
  // feedback.
  if (mode != "ctor")
    trimParam->setValueFast(originalTrim);

  std::vector<ParamInfo> infos(static_cast<size_t>(argc - 9), trimInfo);
  std::vector<std::unique_ptr<FilterGroupComponent>> groups;
  for (int i = 9; i < argc; ++i) {
    auto group = std::make_unique<FilterGroupComponent>(
        FilterGroupComponent::SourcePortConstruction{});
    auto &info = infos.at(static_cast<size_t>(i - 9));
    info.tag = tag;
    info.defaultValue = fromBits(argv[i]);
    group->addParameters(&info, 1);
    handler->addDCAMaster(group.get());
    groups.push_back(std::move(group));
  }
  const bool edit = mode == "provider-L" && action;
  if (mode.rfind("provider-", 0) == 0)
    handler.reset();
  tracing = true;
  if (mode == "onLevel") {
    handler->onLevelChange();
  } else if (mode == "onDCA") {
    handler->onDCAChange(action != 0);
  } else if (mode == "param") {
    handler->paramChanged(tag == 0 ? &level : (tag == 1 ? &trim : nullptr),
                          action);
  } else if (mode == "provider-L") {
    level.setValue(fromBits(argv[4]), edit);
  } else if (mode == "provider-T") {
    trim.setValue(fromBits(argv[3]), false);
  } else if (mode != "ctor") {
    return EXIT_FAILURE;
  }
  tracing = false;
  std::cout << "final " << bits(level.getValue()) << ' '
            << bits(trimParam->getValue()) << '\n';
  handler.reset();
  level.removeObserver(&levelObserver);
  trim.removeObserver(&trimObserver);
  level.setController(nullptr);
  trim.setController(nullptr);
}
