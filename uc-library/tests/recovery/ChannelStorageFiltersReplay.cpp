#include "core/portable/corecomponent.h"
#include "presonus/mixer/ChannelPresetFilter.hpp"
#include <bit>
#include <cstdint>
#include <iostream>
#include <vector>
using namespace Core::Portable;
static const ParamInfo info =
    PARAM_FLOAT(1, "value", -1, 1, 0, 0.1, "", 0, 0, 0);
struct Value : NumericParam {
  Value(int index, std::vector<int> &reads)
      : NumericParam(::info), index(index), reads(reads) {}
  int index;
  std::vector<int> &reads;
  float getValue() const override {
    reads.push_back(index);
    return NumericParam::getValue();
  }
};
struct Observer : IParamObserver {
  void *castTo(TypeID id) override {
    return id == IParamObserver::kTypeID ? this : nullptr;
  }
  void paramChanged(Parameter *, int) override {}
};
struct NotifiedComponent : Component {
  NotifiedComponent() : Component("eq") {}
  int notifications = 0;
  void paramChanged(Parameter *, int) override { ++notifications; }
};
int main() {
  {
    NotifiedComponent controller;
    NumericParam parameter(::info);
    parameter.setController(&controller);
    if (core_cast<Component>(parameter.getController()) != &controller)
      return 3;
    parameter.setValue(0.5f, true);
    if (!controller.notifications)
      return 4;
    parameter.setController(nullptr);
  }
  const char *names[] = {nullptr, "",      "eq", "filter",     "gate",
                         "comp",  "limit", "EQ", "compressor", "eqx"};
  const char *controllers[] = {"",       "",     "comp", "limit", "eq",
                               "filter", "gate", "",     "EQ",    "other"};
  int mode, type, ni, mask, equal, kind, ci;
  uint32_t bits;
  while (std::cin >> mode >> type >> ni >> mask >> bits >> equal >> kind >>
         ci) {
    std::vector<int> reads;
    Value a(0, reads), b(1, reads), c(2, reads);
    float value = std::bit_cast<float>(bits);
    a.setValueFast(value);
    b.setValueFast(value);
    c.setValueFast(value);
    reads.clear();
    Component component(controllers[ci]);
    Observer observer;
    NumericParam parameter(info);
    parameter.setController(ci == 0 ? nullptr
                            : ci == 1
                                ? static_cast<IParamObserver *>(&observer)
                                : static_cast<IParamObserver *>(&component));
    void *object = kind ? &parameter : nullptr;
    int other;
    Presonus::Mixer::ChannelPresetFilter filter(
        equal ? object : &other, mask & 1 ? &a : nullptr,
        mask & 2 ? &b : nullptr, mask & 4 ? &c : nullptr);
    bool result = mode ? filter.shouldSave(type, names[ni], object)
                       : filter.shouldLoad(type, names[ni], object);
    std::cout << "{\"result\":" << result << ",\"reads\":[";
    for (size_t i = 0; i < reads.size(); ++i)
      std::cout << (i ? "," : "") << reads[i];
    std::cout << "]}" << std::endl;
    parameter.setController(nullptr);
  }
}
