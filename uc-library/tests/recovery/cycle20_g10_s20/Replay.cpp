#include "presonus/panel/control.hpp"
#include "presonus/surface_panel/ControlGroup.hpp"

#include <iostream>
#include <memory>
#include <stdexcept>
#include <string_view>
#include <vector>

namespace {
using namespace Core::Portable;
using Presonus::Panel::Control;
using Presonus::Panel::ControlGroup;

struct Numeric final : NumericParam {
  Numeric(const ParamInfo &info, std::vector<int> &trace, int index)
      : NumericParam(info), trace(trace), index(index) {}
  void resetValue(bool edit) override {
    if (!edit)
      throw std::runtime_error("reset did not request edit notification");
    trace.push_back(index);
    NumericParam::resetValue(edit);
  }
  std::vector<int> &trace;
  int index;
};

struct ObservedControl final : Control {
  ObservedControl(std::vector<int> &trace, int index)
      : Control(index), trace(trace), index(index) {}
  bool setParameter(Parameter *parameter, int mode) override {
    if (!parameter) {
      if (mode != 0)
        throw std::runtime_error("unexpected detach mode");
      trace.push_back(index);
    }
    return Control::setParameter(parameter, mode);
  }
  std::vector<int> &trace;
  int index;
};
} // namespace

int main(int argc, char **argv) {
  constexpr int task = 20;
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  std::vector<int> trace;
  std::vector<std::unique_ptr<Numeric>> params;
  std::vector<std::unique_ptr<ObservedControl>> controls;
  ControlGroup group(7, 0);
  for (int index = 0; index + 1 < argc; ++index) {
    auto param = std::make_unique<Numeric>(info, trace, index);
    param->setMin(-10.f);
    param->setMax(10.f);
    param->setDefault(2.f);
    param->setValue(7.f);
    auto control = std::make_unique<ObservedControl>(trace, index);
    if (std::string_view(argv[index + 1]) == "1")
      control->setParameter(param.get(), 0);
    group.add(control.get());
    params.push_back(std::move(param));
    controls.push_back(std::move(control));
  }
  if constexpr (task == 19) {
    group.resetParameters();
    for (const auto &control : controls)
      if (control->getParameter())
        return 1;
  } else {
    group.resetParameterValues();
    for (std::size_t i = 0; i < controls.size(); ++i) {
      const auto *parameter = controls[i]->getParameter();
      if (parameter &&
          (parameter != params[i].get() || parameter->getValue() != 2.f))
        return 1;
      if (!parameter && params[i]->getValue() != 7.f)
        return 1;
    }
  }
  if (group.count() != static_cast<int>(controls.size()))
    return 1;
  for (std::size_t i = 0; i < controls.size(); ++i)
    if (group.at(static_cast<int>(i)) != controls[i].get())
      return 1;
  for (int index : trace)
    std::cout << index << ' ';
  std::cout << '\n';
}
