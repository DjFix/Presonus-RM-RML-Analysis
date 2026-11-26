#include "presonus/uc/ParamHelper.hpp"

#include "core/portable/coreparams.h"
#include "core/public/coreformatter.h"
#include "core/public/coreinterpolator.h"
#include "presonus/uc/parameter_events.hpp"

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <type_traits>

using Core::Portable::NumericParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Core::Portable::StringParam;

namespace {
std::uint32_t word(float value) {
  std::uint32_t bits;
  std::memcpy(&bits, &value, sizeof(bits));
  return bits;
}

class ProbeFormatter : public Core::Formatter {
public:
  ProbeFormatter() : Formatter("observeFormatter") {}
  void print(Data &) const override {}
};

ProbeFormatter formatter;
int oldDestroyed = 0;
int newDestroyed = 0;

class ProbeInterpolator : public Core::Interpolator {
public:
  explicit ProbeInterpolator(bool previous) : previous(previous) {}
  ~ProbeInterpolator() override { ++(previous ? oldDestroyed : newDestroyed); }

  void setRange(float min, float max, float mid) override {
    std::cout << "range " << word(min) << ' ' << word(max) << ' ' << word(mid)
              << '\n';
    Interpolator::setRange(min, max, mid);
  }

private:
  bool previous;
};

template <class Base> class ProbeParameter : public Base {
public:
  explicit ProbeParameter(const ParamInfo &info) : Base(info) {}

  void *castTo(typename Base::TypeID type) override {
    if (type == NumericParam::kTypeID)
      std::cout << "cast " << (this->getFormatter() == &formatter) << '\n';
    return Base::castTo(type);
  }

  void setMin(float value) override {
    if constexpr (std::is_same_v<Base, NumericParam>) {
      std::cout << "install " << (this->getInterpolator() != nullptr) << '\n';
      if (oldDestroyed != 1)
        std::abort();
    }
    std::cout << "min " << word(value) << '\n';
    Base::setMin(value);
  }

  void setMax(float value) override {
    std::cout << "max " << word(value) << '\n';
    Base::setMax(value);
  }

  void setDefault(float value) override {
    std::cout << "default " << word(value) << '\n';
    Base::setDefault(value);
  }
};

void apply(Parameter &parameter, const Presonus::UC::ParamRangeEvent &event) {
  parameter.setFormatter(&formatter);
  ParamHelper::applyRange(&parameter, event);
  std::cout << "formatter " << (parameter.getFormatter() == &formatter) << '\n';
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 9)
    return 2;
  Presonus::UC::ParamRangeEvent event;
  for (std::size_t i = 0; i < event.wordBits.size(); ++i)
    event.wordBits[i] = std::stoul(argv[i + 4]);
  for (std::size_t i = 0; i < event.labels.size(); ++i) {
    const std::string label(argv[i + 2]);
    if (label.size() > event.labels[i].size())
      return 2;
    std::copy(label.begin(), label.end(), event.labels[i].begin());
  }

  Core::FormatterRegistry::add(&formatter);
  Core::InterpolatorFactory::add("observeCurve", []() -> Core::Interpolator * {
    std::cout << "factory observeCurve\n";
    return new ProbeInterpolator(false);
  });

  ParamInfo info{};
  info.minValue = -100.f;
  info.maxValue = 100.f;
  info.flags = ParamInfo::kMutable;
  const bool numeric = std::string(argv[1]) == "1";
  info.type = numeric ? ParamInfo::kFloat : ParamInfo::kString;
  const bool knownCurve = std::string(argv[2]) == "observeCurve";
  if (numeric) {
    ProbeParameter<NumericParam> parameter(info);
    parameter.setInterpolator(new ProbeInterpolator(true));
    apply(parameter, event);
    const auto *curve = parameter.getInterpolator();
    if ((curve != nullptr) != knownCurve || oldDestroyed != 1 ||
        newDestroyed != 0)
      return 3;
    if (word(parameter.getMin()) != event.wordBits[1] ||
        word(parameter.getMax()) != event.wordBits[2] ||
        word(parameter.getDefault()) != event.wordBits[4])
      return 4;
    if (curve && (word(curve->getMinRange()) != event.wordBits[1] ||
                  word(curve->getMaxRange()) != event.wordBits[2] ||
                  word(curve->getMidRange()) != event.wordBits[3]))
      return 5;
  } else {
    ProbeParameter<StringParam> parameter(info);
    apply(parameter, event);
  }
  if (newDestroyed != (numeric && knownCurve ? 1 : 0))
    return 6;
}
