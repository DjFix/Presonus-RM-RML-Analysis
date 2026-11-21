#include "presonus/mixer/FXComponent.hpp"
#include "presonus/mixer_dsp/EqSourceProviders.hpp"

#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>

namespace {
using namespace Core::Portable;

bool failArrayAllocation = false;

unsigned bits(float value) {
  unsigned result;
  std::memcpy(&result, &value, sizeof(result));
  return result;
}

struct App final : presonus::mixer_fx::AppBoundary {
  void setControllerDirty() override {}
  std::uint32_t getTypeNumber() override { return 0; }
  void updateTypeName() override {}
  void handleTypeChange(bool) override {}
};
struct Probe final : NumericParam {
  using NumericParam::NumericParam;
  float getNormalized() const override {
    const auto value = NumericParam::getNormalized();
    std::cout << "1 " << bits(value) << ' ';
    return value;
  }
  void setMin(float value) override {
    std::cout << "4 " << bits(value) << ' ';
    NumericParam::setMin(value);
  }
  void setMax(float value) override {
    std::cout << "5 " << bits(value) << ' ';
    NumericParam::setMax(value);
  }
  void setDefault(float value) override {
    std::cout << "6 " << bits(value) << ' ';
    NumericParam::setDefault(value);
  }
  void setNormalized(float value, bool edit) override {
    std::cout << "7 " << bits(value) << ' ' << edit << ' ';
    NumericParam::setNormalized(value, edit);
  }
};
struct FxProbe final : Presonus::Mixer::FXComponent {
  using FXComponent::FXComponent;
  std::int32_t getEffectTypeInternal(Presonus::EffectType type) override {
    std::cout << "2 " << static_cast<int>(type) << ' ';
    return FXComponent::getEffectTypeInternal(type);
  }
};
struct OldInterpolator final : Core::LinearInterpolator {
  explicit OldInterpolator(int &destroyed)
      : Core::LinearInterpolator(0.f, 1.f), destroyed(destroyed) {}
  ~OldInterpolator() override { ++destroyed; }
  int &destroyed;
};
} // namespace

void *operator new[](std::size_t size) {
  if (!failArrayAllocation)
    if (auto *pointer = std::malloc(size ? size : 1))
      return pointer;
  throw std::bad_alloc();
}
void operator delete[](void *pointer) noexcept { std::free(pointer); }
void operator delete[](void *pointer, std::size_t) noexcept {
  ::operator delete[](pointer);
}

int main() {
  ParamInfo number{};
  number.type = ParamInfo::kFloat;
  number.maxValue = 1;
  ParamInfo string{};
  string.type = ParamInfo::kString;
  int mode, slot, effect;
  float fraction;
  bool registered = false;
  while (std::cin >> mode >> slot >> effect >> fraction) {
    if (mode == 3 && !registered) {
      presonus::dsp::registerEqSourcePortProviders();
      registered = true;
    }
    int retired = 0;
    Probe parameter(number);
    parameter.setValue(fraction, false);
    auto *old = new OldInterpolator(retired);
    parameter.setInterpolator(old);
    StringParam text(string);
    Component owner;
    App app;
    presonus::mixer_fx::State state{owner, parameter, parameter, app};
    presonus::mixer_fx::InterpolatorState interpolation;
    state.interpolation = &interpolation;
    if (mode != 0)
      interpolation.parameters.at(slot) =
          mode == 1 ? static_cast<Parameter *>(&text) : &parameter;
    if (mode == 2 && effect == 1) {
      if (!interpolation.deferred.add(&parameter))
        return 2;
      interpolation.deferred.removeAt(0);
    }

    FxProbe fx(state);
    failArrayAllocation = mode == 4;
    fx.setInterpolator(slot, effect);
    failArrayAllocation = false;
    const auto *result = parameter.getInterpolator();
    if (mode == 3) {
      if (retired != 1 || !result || result == old ||
          result->getMinRange() != parameter.getMin() ||
          result->getMaxRange() != parameter.getMax() ||
          result->getMidRange() != parameter.getDefault())
        return 3;
      std::cout << bits(result->getMinRange()) << ' '
                << bits(result->getMaxRange()) << ' '
                << bits(result->getMidRange()) << ' ';
    } else if (retired || result != old) {
      return 4;
    }
    if (interpolation.deferred.count() &&
        interpolation.deferred.at(0) != &parameter)
      return 5;
    std::cout << interpolation.deferred.count() << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
